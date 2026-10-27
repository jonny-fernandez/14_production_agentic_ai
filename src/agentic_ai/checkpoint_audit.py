"""CP3 opt-in, read-only offline checkpoint review.

Evaluates internal invariants before an operator trusts/resumes a saved local state.
This is neither authenticated provenance nor a replacement for the engine's
authorization and approval checks. No arbitrary tools or external services run.
Only bounded redacted metadata leaves this module.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import math
from typing import Any, Iterable

from agentic_ai.authorization import authorize
from agentic_ai.contracts import MetricsOutput, RetrievalOutput, ReportOutput
from agentic_ai.decision_controls import PlanRejectedError, validated_plan
from agentic_ai.state import AgentState
from agentic_ai.workflow import digest
from agentic_ai.telemetry import ALLOWED_NODES, ALLOWED_STATES

TOOL_SCHEMAS = {
    "calculate_metrics": MetricsOutput,
    "retrieve_documents": RetrievalOutput,
    "save_report": ReportOutput,
}
TRACE_FIELDS = frozenset({"node", "status_before", "status_after", "step_index",
                          "elapsed_ms", "evidence_count", "tool_call_count"})
CALL_STATUSES = frozenset({"success", "failed", "blocked"})
_FAILURE_OUTCOMES = frozenset({"failed", "invalid", "unauthorized"})


def _safe_id_hash(request_id: str) -> str:
    return hashlib.sha256(str(request_id).encode("utf-8")).hexdigest()[:16]


def audit_checkpoint(data: AgentState | dict[str, Any]) -> dict[str, Any]:
    """Review state without executing tools, writing data or exporting raw fields.

    PASS: structurally safe to *consider* normal workflow actions; NOT an
    authorization grant. QUARANTINE: inconsistent or deliberately failed state;
    do not automatically resume, approve, or publish its contents.
    """
    try:
        state = data if isinstance(data, AgentState) else AgentState.model_validate(data)
    except Exception:
        return {"status": "QUARANTINE", "codes": ["INVALID_STATE"],
                "request_id_sha256_prefix": None, "tool_evidence_count": 0}

    issues: set[str] = set()
    try:
        canonical = validated_plan(state.task_type, state.plan)
    except PlanRejectedError:
        canonical = []
        issues.add("UNTRUSTED_PLAN")
    if state.plan != canonical or not (0 <= state.step_index <= len(canonical)):
        issues.add("INVALID_CURSOR_OR_PLAN")
    if state.status in _FAILURE_OUTCOMES:
        issues.add("FAILED_OR_UNAUTHORIZED_STATE")

    executed = [t for t in canonical[:min(state.step_index, len(canonical))] if t in TOOL_SCHEMAS]
    if len(state.evidence) != len(executed):
        issues.add("EVIDENCE_COUNT_MISMATCH")
    for index, item in enumerate(state.evidence):
        if not isinstance(item, dict) or index >= len(executed) or item.get("tool") != executed[index]:
            issues.add("EVIDENCE_ORDER_INVALID")
            continue
        try:
            if item.get("sha256") != digest(item.get("output")):
                issues.add("EVIDENCE_DIGEST_INVALID")
            TOOL_SCHEMAS[executed[index]].model_validate(item.get("output"))
        except (TypeError, ValueError, OverflowError):
            issues.add("EVIDENCE_SCHEMA_INVALID")

    expected_calls = Counter()
    for item in state.tool_calls:
        if not isinstance(item, dict) or item.get("tool") not in TOOL_SCHEMAS or item.get("status") not in CALL_STATUSES:
            issues.add("INVALID_TOOL_CALL")
            continue
        name = item["tool"]
        if name not in canonical or not authorize(state.role, name):
            issues.add("UNAUTHORIZED_TOOL_CALL")
        if (not isinstance(item.get("attempt"), int) or isinstance(item.get("attempt"), bool)
                or not 1 <= item["attempt"] <= 3):
            issues.add("INVALID_ATTEMPT")
        expected_calls[name] += 1
    if expected_calls["save_report"] > 1:
        issues.add("WRITE_RETRIED")

    approval = state.approval
    if approval is not None:
        if (state.task_type != "report" or not isinstance(approval, dict)
                or type(approval.get("approved")) is not bool
                or approval.get("tool") != "save_report"
                or not isinstance(approval.get("step_index"), int)
                or isinstance(approval.get("step_index"), bool)
                or approval.get("step_index") != (canonical.index("request_approval") if "request_approval" in canonical else -1)
                or not isinstance(approval.get("reviewer"), str)
                or not 3 <= len(approval["reviewer"].strip()) <= 64
                or not isinstance(approval.get("reason"), str)
                or not 5 <= len(approval["reason"].strip()) <= 256):
            issues.add("INVALID_APPROVAL_RECORD")
    if any(isinstance(e, dict) and e.get("tool") == "save_report" for e in state.evidence):
        if not isinstance(approval, dict) or approval.get("approved") is not True or state.dry_run:
            issues.add("UNAPPROVED_WRITE_EVIDENCE")
    if state.status == "running" and (state.final_answer is not None or approval is not None and "request_approval" in canonical and state.step_index <= canonical.index("request_approval")):
        issues.add("PREMATURE_TERMINAL_OR_APPROVAL")
    if state.status == "awaiting_approval":
        if (state.task_type != "report" or approval is not None or
                not 0 <= state.step_index < len(canonical) or
                canonical[state.step_index] != "request_approval"):
            issues.add("INVALID_APPROVAL_PAUSE")
    if state.status == "success":
        if state.step_index != len(canonical) or not state.final_answer or not executed:
            issues.add("INVALID_SUCCESS_CLAIM")
        if state.task_type == "report" and (not isinstance(approval, dict) or approval.get("approved") is not True):
            issues.add("INVALID_SUCCESS_CLAIM")
    if state.status in {"rejected", "dry_run"}:
        if (state.task_type != "report" or not 0 <= state.step_index < len(canonical)
                or canonical[state.step_index] != "request_approval"
                or (state.status == "dry_run" and (not state.dry_run or approval is not None))
                or (state.status == "rejected" and (not isinstance(approval, dict) or approval.get("approved") is not False))):
            issues.add("INVALID_TERMINAL_GATE")
    if state.status == "no_evidence":
        if (not 0 <= state.step_index < len(canonical) or
                canonical[state.step_index] != "retrieve_documents" or
                any(isinstance(e, dict) and e.get("tool") == "save_report" for e in state.evidence)):
            issues.add("INVALID_NO_EVIDENCE_CLAIM")

    for event in state.trace_events:
        if not isinstance(event, dict) or set(event) != TRACE_FIELDS:
            issues.add("TRACE_NOT_REDACTED")
            continue
        if (event.get("node") not in (ALLOWED_NODES | {"unrecognized"}) or
                event.get("status_before") not in ALLOWED_STATES or
                event.get("status_after") not in ALLOWED_STATES):
            issues.add("TRACE_NOT_REDACTED")
        duration = event.get("elapsed_ms")
        if (type(duration) not in (float, int) or not math.isfinite(duration) or duration < 0):
            issues.add("INVALID_TRACE_DURATION")
        for key in ("step_index", "evidence_count", "tool_call_count"):
            if type(event.get(key)) is not int or event[key] < 0:
                issues.add("TRACE_NOT_REDACTED")
    return {"status": "QUARANTINE" if issues else "PASS", "codes": sorted(issues),
            "request_id_sha256_prefix": _safe_id_hash(state.request_id),
            "tool_evidence_count": len(state.evidence)}


def audit_batch(states: Iterable[AgentState | dict[str, Any]], *, max_states: int = 500) -> dict[str, Any]:
    """Bounded batch rollup; export reason codes, never queries or raw reports."""
    if type(max_states) is not int or not 1 <= max_states <= 10000:
        raise ValueError("max_states must be an integer from 1 to 10000")
    decisions = []
    for item in states:
        if len(decisions) >= max_states:
            raise ValueError("Batch exceeds configured review bound")
        decisions.append(audit_checkpoint(item))
    return {"status": "NOT_VERIFIED" if not decisions else ("PASS" if all(i["status"] == "PASS" for i in decisions) else "QUARANTINE"),
            "total": len(decisions), "quarantined": sum(i["status"] == "QUARANTINE" for i in decisions),
            "results": decisions}
