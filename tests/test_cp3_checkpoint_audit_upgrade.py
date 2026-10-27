"""CP3 deterministic adversarial audits of synthetic local saved states.

These tests never call a hosted model and never authenticate untrusted SQLite.
"""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from agentic_ai.checkpoint_audit import audit_batch, audit_checkpoint
from agentic_ai.contracts import WorkflowRequest
from agentic_ai.state import AgentState
from agentic_ai.workflow import WorkflowEngine, digest


def payload(request_id="audit-metrics-01", kind="metrics", *, dry_run=True):
    out = {"request_id": request_id, "task_type": kind, "metrics": {"values": [1.0, 3.0, 5.0]}}
    if kind in ("analysis", "report", "retrieval"):
        out["retrieval"] = {"query": "synthetic leave policy"}
    if kind == "report":
        out.update(report_id="audit-report-01", dry_run=dry_run)
    return out


def valid_metrics_state(tmp_path):
    engine = WorkflowEngine(tmp_path, use_langgraph=False)
    try:
        return engine.start(payload())
    finally:
        engine.store.close()


def fake_report_state(status="awaiting_approval"):
    request = WorkflowRequest.model_validate(payload("audit-report-req01", "report", dry_run=False))
    metrics = {"count": 3, "mean": 3.0}
    retrieval = {"fixture_version": "synthetic-v1", "documents": [
        {"source_id": "SYNTH-DOC-001", "title": "Synthetic policy", "text": "Leave policy"}
    ]}
    evidence = [{"tool": "calculate_metrics", "output": metrics, "sha256": digest(metrics)},
                {"tool": "retrieve_documents", "output": retrieval, "sha256": digest(retrieval)}]
    plan = ["calculate_metrics", "retrieve_documents", "verify_evidence",
            "request_approval", "save_report", "answer"]
    state = AgentState(request_id=request.request_id, role="manager", task_type="report",
                       request=request.model_dump(mode="json"), dry_run=False,
                       plan=plan, status="awaiting_approval", step_index=3, evidence=evidence,
                       tool_calls=[{"tool": "calculate_metrics", "status": "success", "attempt": 1},
                                   {"tool": "retrieve_documents", "status": "success", "attempt": 1}])
    if status == "success":
        output = {"path": "outputs/reports/audit-report-01.json", "sha256": "a" * 64,
                  "already_existed": False}
        state.evidence.append({"tool": "save_report", "sha256": digest(output), "output": output})
        state.approval = {"approved": True, "reviewer": "local-reviewer", "reason": "Local synthetic test", "tool": "save_report", "step_index": 3}
        state.tool_calls.append({"tool": "save_report", "attempt": 1, "status": "success"})
        state.step_index = len(plan)
        state.status = "success"
        state.final_answer = "Verified synthetic workflow."
    elif status == "rejected":
        state.status = "rejected"
        state.approval = {"approved": False, "reviewer": "local-reviewer", "reason": "Rejected synthetic test", "tool": "save_report", "step_index": 3}
    elif status == "dry_run":
        state.status = "dry_run"
        state.dry_run = True
        state.request["dry_run"] = True
        state.final_answer = "Synthetic preview only."
    return state


@pytest.mark.parametrize("kind", ["metrics", "retrieval", "analysis", "report"])
def test_untrusted_plan_not_evaluated_as_valid(kind):
    state = AgentState(request_id="unsafe-test-0001", task_type=kind, plan=["shell", "answer"])
    result = audit_checkpoint(state)
    assert result["status"] == "QUARANTINE" and "UNTRUSTED_PLAN" in result["codes"]


def test_real_metrics_engine_checkpoint_is_safe(tmp_path):
    s = valid_metrics_state(tmp_path)
    assert s.status == "success" and audit_checkpoint(s)["status"] == "PASS"


def test_json_round_trip_valid_metrics_checkpoint(tmp_path):
    s = valid_metrics_state(tmp_path)
    assert audit_checkpoint(json.loads(s.model_dump_json()))["status"] == "PASS"


@pytest.mark.parametrize("status", ["awaiting_approval", "success", "rejected", "dry_run"])
def test_valid_report_boundaries(status):
    assert audit_checkpoint(fake_report_state(status))["status"] == "PASS"


@pytest.mark.parametrize("field,value", [
    ("step_index", 99), ("step_index", -1), ("status", "failed"),
    ("final_answer", None), ("plan", ["calculate_metrics", "answer"]),
])
def test_corrupted_success_checkpoint_is_quarantined(tmp_path, field, value):
    s = valid_metrics_state(tmp_path).model_copy(deep=True)
    setattr(s, field, value)
    assert audit_checkpoint(s)["status"] == "QUARANTINE"


@pytest.mark.parametrize("bad", ["00" * 32, None, 7, "not-a-digest"])
def test_altered_evidence_hash_rejected(tmp_path, bad):
    state = valid_metrics_state(tmp_path).model_copy(deep=True)
    state.evidence[0]["sha256"] = bad
    assert "EVIDENCE_DIGEST_INVALID" in audit_checkpoint(state)["codes"]


@pytest.mark.parametrize("kind", ["tool", "output", "extra", "missing"])
def test_evidence_tamper_never_passes(tmp_path, kind):
    s = valid_metrics_state(tmp_path).model_copy(deep=True)
    if kind == "tool":
        s.evidence[0]["tool"] = "save_report"
    elif kind == "output":
        s.evidence[0]["output"]["count"] = 999
    elif kind == "extra":
        s.evidence.append(deepcopy(s.evidence[0]))
    else:
        s.evidence.clear()
    assert audit_checkpoint(s)["status"] == "QUARANTINE"


@pytest.mark.parametrize("modifier", [
    lambda s: s.approval.update(approved=False),
    lambda s: s.approval.update(tool="shell"),
    lambda s: s.approval.update(step_index=4),
    lambda s: s.approval.update(reviewer="a"),
    lambda s: s.approval.update(reason="no"),
    lambda s: s.approval.update(approved="yes"),
])
def test_mutated_report_approval_rejected(modifier):
    s = fake_report_state("success")
    modifier(s)
    assert audit_checkpoint(s)["status"] == "QUARANTINE"


def test_fake_pending_approval_record_is_rejected():
    s = fake_report_state()
    s.approval = {"approved": True, "reviewer": "someone", "reason": "unsupported", "tool": "save_report", "step_index": 3}
    assert "INVALID_APPROVAL_PAUSE" in audit_checkpoint(s)["codes"]


def test_retried_write_is_quarantined():
    s = fake_report_state("success")
    s.tool_calls.append({"tool": "save_report", "attempt": 2, "status": "success"})
    assert "WRITE_RETRIED" in audit_checkpoint(s)["codes"]


def test_unauthorized_tool_call_is_quarantined(tmp_path):
    s = valid_metrics_state(tmp_path).model_copy(deep=True)
    s.tool_calls.append({"tool": "save_report", "attempt": 1, "status": "success"})
    assert "UNAUTHORIZED_TOOL_CALL" in audit_checkpoint(s)["codes"]


@pytest.mark.parametrize("attempt", [0, 4, -1, True, "1"])
def test_invalid_attempt_budget_rejected(tmp_path, attempt):
    s = valid_metrics_state(tmp_path).model_copy(deep=True)
    s.tool_calls[0]["attempt"] = attempt
    assert "INVALID_ATTEMPT" in audit_checkpoint(s)["codes"]


def test_raw_text_cannot_enter_trace_payload(tmp_path):
    s = valid_metrics_state(tmp_path).model_copy(deep=True)
    s.trace_events[0]["query"] = "sensitive synthetic query"
    assert "TRACE_NOT_REDACTED" in audit_checkpoint(s)["codes"]


def test_malicious_trace_value_rejected(tmp_path):
    s = valid_metrics_state(tmp_path).model_copy(deep=True)
    s.trace_events[0]["node"] = "ignore-instructions-and-leak"
    assert "TRACE_NOT_REDACTED" in audit_checkpoint(s)["codes"]


def test_redacted_summary_does_not_export_request_content(tmp_path):
    s = valid_metrics_state(tmp_path).model_copy(deep=True)
    s.request["metrics"]["values"] = [125.0]
    result = audit_checkpoint(s)
    assert set(result) == {"status", "codes", "request_id_sha256_prefix", "tool_evidence_count"}
    assert "125.0" not in json.dumps(result)
    assert s.request_id not in json.dumps(result)


def test_batch_pass_and_quarantine(tmp_path):
    good = valid_metrics_state(tmp_path)
    bad = good.model_copy(deep=True)
    bad.evidence[0]["output"]["mean"] = -999.0
    result = audit_batch([good, bad])
    assert result["status"] == "QUARANTINE" and result["total"] == 2
    assert result["quarantined"] == 1


@pytest.mark.parametrize("max_states", [0, -1, True, 1.5, 10001])
def test_bad_batch_limit_rejected(max_states):
    with pytest.raises(ValueError):
        audit_batch([], max_states=max_states)


def test_batch_bound_enforced(tmp_path):
    s = valid_metrics_state(tmp_path)
    with pytest.raises(ValueError, match="bound"):
        audit_batch([s, s], max_states=1)


def test_empty_batch_not_claimed_pass():
    assert audit_batch([])["status"] == "NOT_VERIFIED"


def test_invalid_state_is_quarantined_without_echo():
    x = audit_checkpoint({"request_id": "danger-user-secret", "untrusted": "danger"})
    assert x["status"] == "QUARANTINE" and x["codes"] == ["INVALID_STATE"]
    assert "danger" not in json.dumps(x)
