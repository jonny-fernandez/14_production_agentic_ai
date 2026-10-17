"""CP1 deterministic one-tool baseline, NOT a multi-step LangGraph agent."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from agentic_ai.contracts import (
    BaselineResult, MetricsInput, MetricsOutput, Outcome, RetrievalInput, RetrievalOutput
)
from agentic_ai.tools.mock_tools import calculate_metrics, retrieval_adapter
from agentic_ai.tools.registry import (
    ToolContractError, ToolExecutionError, ToolRegistry, UnauthorizedToolError, UnknownToolError
)

TASK_TOOL = {"metrics": "calculate_metrics", "retrieval": "retrieve_documents"}


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("calculate_metrics", calculate_metrics, input_model=MetricsInput, output_model=MetricsOutput)
    registry.register("retrieve_documents", retrieval_adapter, input_model=RetrievalInput, output_model=RetrievalOutput)
    return registry


def run_baseline(task_type: str, arguments: dict[str, Any], *, role: str = "analyst") -> BaselineResult:
    """Bounded read-only execution; each invocation has at most one tool call."""
    tool = TASK_TOOL.get(task_type)
    if tool is None:
        return BaselineResult(task_type="unsupported", status=Outcome.UNSUPPORTED, answer="Unsupported task; no tool was run.")
    try:
        output = make_registry().execute(tool, arguments, role=role)
    except UnauthorizedToolError:
        return BaselineResult(task_type=task_type, status=Outcome.UNAUTHORIZED, selected_tool=tool,
                              answer="Access denied; no tool was run.")
    except (ToolContractError, UnknownToolError):
        return BaselineResult(task_type=task_type, status=Outcome.INVALID_INPUT, selected_tool=tool,
                              answer="Invalid tool request or result; no verified answer is available.")
    except ToolExecutionError:
        return BaselineResult(task_type=task_type, status=Outcome.FAILED, selected_tool=tool,
                              answer="Tool execution failed; no verified answer is available.")

    source_ids: list[str] = []
    if task_type == "retrieval":
        source_ids = [doc["source_id"] for doc in output["documents"]]
        if not source_ids:
            return BaselineResult(task_type=task_type, status=Outcome.NO_EVIDENCE, selected_tool=tool,
                                  tool_output=output, answer="No matching evidence exists in the synthetic corpus.")
        answer = f"Retrieved {len(source_ids)} synthetic source(s): {', '.join(source_ids)}. No factual summary is inferred."
    else:
        answer = f"Verified sample mean: {output['mean']}; count: {output['count']}."
    digest = hashlib.sha256(json.dumps(output, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False).encode("utf-8")).hexdigest()
    return BaselineResult(task_type=task_type, status=Outcome.SUCCESS, selected_tool=tool,
                          tool_output=output, evidence_sha256=digest, source_ids=source_ids, answer=answer)
