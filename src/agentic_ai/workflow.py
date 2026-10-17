"""CP2 deterministic, bounded orchestration of synthetic tools.

LangGraph is used when installed; the same step function has a native test
runner for environments without LangGraph. No LLM determines execution success.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, TypedDict

from agentic_ai.authorization import authorize
from agentic_ai.telemetry import trace_id_for, redact_event, monotonic_ns
from agentic_ai.contracts import (MetricsInput, MetricsOutput, RetrievalInput,
                                  RetrievalOutput, ReportInput, ReportOutput,
                                  WorkflowRequest)
from agentic_ai.state import AgentState
from agentic_ai.state_store import SQLiteStateStore, StateConflictError
from agentic_ai.tools.registry import (ToolRegistry, ToolExecutionError,
                                       ToolContractError, UnauthorizedToolError,
                                       UnknownToolError)
from agentic_ai.tools.mock_tools import calculate_metrics, retrieval_adapter
from agentic_ai.tools.report_tool import make_report_tool


class GraphEnvelope(TypedDict):
    state: dict[str, Any]


class ApprovalError(ValueError):
    pass


def digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_cp2_registry(root: Path) -> ToolRegistry:
    registry = ToolRegistry(allow_write_registration=True)
    registry.register("calculate_metrics", calculate_metrics,
                      input_model=MetricsInput, output_model=MetricsOutput)
    registry.register("retrieve_documents", retrieval_adapter,
                      input_model=RetrievalInput, output_model=RetrievalOutput)
    registry.register("save_report", make_report_tool(root), input_model=ReportInput,
                      output_model=ReportOutput, read_only=False)
    return registry


class WorkflowEngine:
    """SQLite-persisted workflow (not thread-safe per engine instance).

    The caller chooses a trusted local role; production API supplies role from
    credentials, not a request body. Every tool action is allowlisted.
    """

    def __init__(self, root: Path, *, registry: ToolRegistry | None = None,
                 store: SQLiteStateStore | None = None, use_langgraph: bool = True,
                 max_steps: int = 8, max_read_attempts: int = 2):
        self.root = Path(root).resolve()
        self.registry = registry or make_cp2_registry(self.root)
        self.store = store or SQLiteStateStore(str(self.root / "outputs" / "cp2_state.sqlite3"))
        self.max_steps = max_steps
        self.max_read_attempts = max_read_attempts
        if not 1 <= max_steps <= 20 or not 1 <= max_read_attempts <= 3:
            raise ValueError("Invalid bounded execution budgets")
        self.graph = self._build_graph() if use_langgraph else None

    def _build_graph(self):
        try:
            from langgraph.graph import StateGraph, START, END
        except ImportError:
            return None
        builder = StateGraph(GraphEnvelope)
        builder.add_node("execute_step", self._graph_step)
        builder.add_edge(START, "execute_step")
        builder.add_conditional_edges("execute_step", self._graph_route,
                                      {"again": "execute_step", "end": END})
        return builder.compile()

    @staticmethod
    def _graph_route(data: GraphEnvelope) -> str:
        return "again" if data["state"]["status"] == "running" else "end"

    def _graph_step(self, data: GraphEnvelope) -> GraphEnvelope:
        state = AgentState.model_validate(data["state"])
        self._traced_step(state)
        self.store.save(state)
        return {"state": state.model_dump(mode="json")}

    def _drive(self, state: AgentState) -> AgentState:
        if self.graph is not None:
            output = self.graph.invoke({"state": state.model_dump(mode="json")},
                                       config={"recursion_limit": 2 * self.max_steps + 5})
            return AgentState.model_validate(output["state"])
        while state.status == "running":
            self._traced_step(state)
            self.store.save(state)
        return state

    def start(self, request: WorkflowRequest | dict, *, role: str = "analyst") -> AgentState:
        request = WorkflowRequest.model_validate(request)
        plans = {
            "metrics": ["calculate_metrics", "verify_evidence", "answer"],
            "retrieval": ["retrieve_documents", "verify_evidence", "answer"],
            "analysis": ["calculate_metrics", "retrieve_documents", "verify_evidence", "answer"],
            "report": ["calculate_metrics", "retrieve_documents", "verify_evidence", "request_approval", "save_report", "answer"],
        }
        state = AgentState(request_id=request.request_id, task_type=request.task_type,
                           role=role, request=request.model_dump(mode="json"),
                           dry_run=request.dry_run, plan=plans[request.task_type],
                           trace_id=trace_id_for(request.request_id))
        if len(state.plan) > self.max_steps:
            raise ValueError("Plan exceeds execution budget")
        # Fail closed before using ANY tool when the role lacks a required step.
        for step in state.plan:
            if step in {"calculate_metrics", "retrieve_documents", "save_report"} and (
                step not in self.registry.names() or not authorize(role, step)
            ):
                state.status = "unauthorized"
                state.error = "Workflow contains an unauthorized or unregistered tool"
                break
        self.store.create(state)  # duplicate requests never repeat tool side effects
        return self._drive(state)

    def resume(self, request_id: str) -> AgentState:
        state = self.store.load(request_id)
        if state is None:
            raise KeyError("Unknown request ID")
        if state.status == "awaiting_approval" and state.approval is None:
            return state
        if state.status in {"success", "failed", "rejected", "unauthorized", "no_evidence", "dry_run", "invalid"}:
            return state
        if state.status == "awaiting_approval":
            state.status = "running"
            self.store.save(state)
        return self._drive(state)

    def decide(self, request_id: str, *, reviewer: str, approved: bool, reason: str) -> AgentState:
        state = self.store.load(request_id)
        if state is None:
            raise KeyError("Unknown request ID")
        if state.status != "awaiting_approval" or state.approval is not None:
            raise ApprovalError("No outstanding approval request")
        if not isinstance(approved, bool) or not isinstance(reviewer, str) or not (3 <= len(reviewer.strip()) <= 64):
            raise ApprovalError("Named reviewer and an explicit boolean decision required")
        if not isinstance(reason, str) or not (5 <= len(reason.strip()) <= 256):
            raise ApprovalError("A concise reason is required")
        state.approval = {"approved": approved, "reviewer": reviewer.strip(), "reason": reason.strip(),
                          "step_index": state.step_index, "tool": "save_report"}
        state.status = "running"
        self.store.save(state)
        return self._drive(state)

    @staticmethod
    def _verified(state: AgentState) -> bool:
        """Check complete, ordered, typed provenance for tools already executed.

        Detects accidental or modified checkpoint evidence, but does NOT
        authenticate an attacker-writable SQLite database or external records.
        """
        tool_schemas = {
            "calculate_metrics": MetricsOutput,
            "retrieve_documents": RetrievalOutput,
            "save_report": ReportOutput,
        }
        expected = [node for node in state.plan[:state.step_index] if node in tool_schemas]
        if not expected or len(expected) != len(state.evidence):
            return False
        try:
            for name, item in zip(expected, state.evidence):
                if not isinstance(item, dict) or item.get("tool") != name:
                    return False
                if item.get("sha256") != digest(item.get("output")):
                    return False
                tool_schemas[name].model_validate(item.get("output"))
        except (ValueError, TypeError, OverflowError):
            return False
        return True

    def _tool_arguments(self, state: AgentState, tool: str) -> dict:
        req = state.request
        if tool == "calculate_metrics":
            return req["metrics"]
        if tool == "retrieve_documents":
            return req["retrieval"]
        if tool == "save_report":
            by_tool = {e["tool"]: e for e in state.evidence}
            metric = by_tool["calculate_metrics"]["output"]
            documents = by_tool["retrieve_documents"]["output"]["documents"]
            return {"report_id": req["report_id"], "metrics": metric,
                    "source_ids": [d["source_id"] for d in documents],
                    "evidence_sha256": [by_tool["calculate_metrics"]["sha256"],
                                        by_tool["retrieve_documents"]["sha256"]]}
        raise UnknownToolError("Unknown planned tool")

    def _traced_step(self, state: AgentState) -> None:
        """Measure local step duration and record only allowlisted metadata."""
        index, before = state.step_index, state.status
        node = state.plan[index] if 0 <= index < len(state.plan) else "unrecognized"
        start = monotonic_ns()
        try:
            self._step(state)
        finally:
            state.trace_events.append(redact_event(
                node=node, before=before, after=state.status, step_index=index,
                elapsed_ns=monotonic_ns() - start,
                evidence_count=len(state.evidence), tool_call_count=len(state.tool_calls),
            ))

    def _step(self, state: AgentState) -> None:
        if state.status != "running":
            return
        if state.step_index >= len(state.plan) or state.step_index >= self.max_steps:
            state.status = "failed"
            state.error = "Bounded plan exhausted without completion"
            return
        step = state.plan[state.step_index]
        if step == "verify_evidence":
            if not self._verified(state):
                state.status = "failed"
                state.error = "Evidence failed verification"
                return
        elif step == "request_approval":
            if state.dry_run:
                state.status = "dry_run"
                state.final_answer = "Synthetic report preview validated; no file was written or approval recorded."
                return
            if state.approval is None:
                state.status = "awaiting_approval"
                return
            if not state.approval.get("approved") or state.approval.get("tool") != "save_report":
                state.status = "rejected"
                state.final_answer = "Local report action was rejected; nothing was written."
                return
            if not self._verified(state):
                state.status = "failed"
                state.error = "Evidence invalid before approved action"
                return
        elif step == "answer":
            if not self._verified(state):
                state.status = "failed"
                state.error = "Unsupported answer without verified evidence"
                return
            evidence = {x["tool"]: x for x in state.evidence}
            parts = ["Verified synthetic workflow"]
            if "calculate_metrics" in evidence:
                item = evidence["calculate_metrics"]["output"]
                parts.append(f"mean={item['mean']}; count={item['count']}")
            if "retrieve_documents" in evidence:
                ids = [d["source_id"] for d in evidence["retrieve_documents"]["output"]["documents"]]
                parts.append("sources=" + ",".join(ids))
            if "save_report" in evidence:
                parts.append("locally saved=" + evidence["save_report"]["output"]["path"])
            state.final_answer = "; ".join(parts) + ". No real account, company data or LLM was used."
            state.status = "success"
            state.step_index += 1
            return
        else:
            # Never trust planned steps to be a valid or authorized tool name.
            if step not in {"calculate_metrics", "retrieve_documents", "save_report"}:
                state.status = "failed"
                state.error = "Unknown plan node"
                return
            if step == "save_report" and (state.dry_run or not state.approval or not state.approval.get("approved")):
                state.status = "unauthorized"
                state.error = "Missing approved write decision"
                return
            if step == "save_report" and not self._verified(state):
                state.status = "failed"
                state.error = "No verified inputs to write tool"
                return
            args = self._tool_arguments(state, step)
            try:
                read_only = self.registry.is_read_only(step)
                attempts = self.max_read_attempts if read_only else 1
                for attempt in range(1, attempts + 1):
                    try:
                        result = self.registry.execute(step, args, role=state.role,
                                                       approval_granted=step == "save_report" and bool(state.approval and state.approval["approved"]))
                        state.tool_calls.append({"tool": step, "attempt": attempt, "status": "success"})
                        break
                    except ToolExecutionError:
                        state.tool_calls.append({"tool": step, "attempt": attempt, "status": "failed"})
                        if attempt == attempts:
                            raise
            except UnauthorizedToolError:
                state.status = "unauthorized"
                state.error = "Tool authorization denied"
                return
            except (ToolExecutionError, ToolContractError, UnknownToolError):
                state.status = "failed"
                state.error = "Tool execution or validation failed"
                return
            if step == "retrieve_documents" and not result["documents"]:
                state.status = "no_evidence"
                state.final_answer = "No matching synthetic evidence. No report created or claim inferred."
                return
            state.evidence.append({"tool": step, "sha256": digest(result), "output": result})
        state.step_index += 1
