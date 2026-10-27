"""Six offline synthetic checkpoint gate probes; no LLM or external service."""
from __future__ import annotations

from copy import deepcopy
import json
import tempfile
from pathlib import Path

from agentic_ai.checkpoint_audit import audit_checkpoint
from agentic_ai.workflow import WorkflowEngine


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p14_cp3_probes_") as temp:
        engine = WorkflowEngine(Path(temp), use_langgraph=False)
        try:
            state = engine.start({"request_id": "probe-metrics-01", "task_type": "metrics",
                                  "metrics": {"values": [1.0, 2.0, 3.0]}})
        finally:
            engine.store.close()
        expected = []
        expected.append(audit_checkpoint(state)["status"] == "PASS")
        tampered = state.model_copy(deep=True)
        tampered.evidence[0]["output"]["mean"] = -200.0
        expected.append("EVIDENCE_DIGEST_INVALID" in audit_checkpoint(tampered)["codes"])
        plan = state.model_copy(deep=True)
        plan.plan = ["save_report", "answer"]
        expected.append("UNTRUSTED_PLAN" in audit_checkpoint(plan)["codes"])
        trace = state.model_copy(deep=True)
        trace.trace_events[0]["request_payload"] = "NO_RAW_PROMPTS_IN_REPORT"
        expected.append("TRACE_NOT_REDACTED" in audit_checkpoint(trace)["codes"])
        failed = state.model_copy(deep=True)
        failed.status = "failed"
        expected.append("FAILED_OR_UNAUTHORIZED_STATE" in audit_checkpoint(failed)["codes"])
        no_grant = state.model_copy(deep=True)
        no_grant.tool_calls.append({"tool": "save_report", "status": "success", "attempt": 1})
        expected.append("UNAUTHORIZED_TOOL_CALL" in audit_checkpoint(no_grant)["codes"])
    hits = sum(expected)
    print(f"CP3_ADVERSARIAL_PROBES: {hits}/6", flush=True)
    print("CP3_READ_ONLY: TRUE", flush=True)
    print("CP3_LOCAL_SYNTHETIC_ONLY: TRUE", flush=True)
    return 0 if hits == len(expected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
