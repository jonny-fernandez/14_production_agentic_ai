"""Opt-in plan and reliability controls. Offline, synthetic test scenarios."""
from __future__ import annotations

import pytest

from agentic_ai.decision_controls import (CANONICAL_PLANS, ALTERNATE_ANALYSIS,
    PlanRejectedError, ReadToolCircuit, validated_plan)
from agentic_ai.workflow import WorkflowEngine, ApprovalError, make_cp2_registry
from agentic_ai.tools.registry import ToolDefinition
from agentic_ai.contracts import MetricsInput, MetricsOutput

ARGS = {"metrics": {"values": [10, 20, 30]}, "retrieval": {"query": "leave policy"}}


def request(request_id, kind="analysis", **kwargs):
    return {"request_id": request_id, "task_type": kind, **ARGS, **kwargs}


@pytest.mark.parametrize("kind", ["metrics", "retrieval", "analysis", "report"])
def test_default_plans_match_baseline(kind):
    assert validated_plan(kind) == list(CANONICAL_PLANS[kind])


def test_only_independent_read_steps_can_be_reordered(tmp_path):
    e = WorkflowEngine(tmp_path, use_langgraph=False)
    s = e.start(request("read-order-01"), proposed_plan=list(ALTERNATE_ANALYSIS))
    assert s.status == "success"
    assert [x["tool"] for x in s.evidence] == ["retrieve_documents", "calculate_metrics"]
    assert "mean=20.0" in s.final_answer and "sources=" in s.final_answer
    assert e.store.load(s.request_id).plan == list(ALTERNATE_ANALYSIS)
    e.store.close()


@pytest.mark.parametrize("plan", [
    ["calculate_metrics", "answer"],
    ["calculate_metrics", "retrieve_documents", "answer"],
    ["save_report", "verify_evidence", "answer"],
    ["calculate_metrics", "retrieve_documents", "verify_evidence", "save_report", "answer"],
    ["calculate_metrics", "calculate_metrics", "retrieve_documents", "verify_evidence", "answer"],
    ["shell", "calculate_metrics", "retrieve_documents", "verify_evidence", "answer"],
    ["retrieve_documents", "calculate_metrics", "request_approval", "answer"],
    "calculate_metrics",
    [],
    [42],
])
def test_untrusted_proposals_rejected_without_tool_calls(tmp_path, plan):
    e = WorkflowEngine(tmp_path, use_langgraph=False)
    with pytest.raises(PlanRejectedError):
        e.start(request("bad-proposal-01"), proposed_plan=plan)
    assert e.store.load("bad-proposal-01") is None
    assert not list((tmp_path / "outputs" / "reports").glob("*.json")) if (tmp_path / "outputs" / "reports").exists() else True
    e.store.close()


def test_report_must_retain_approval_before_write(tmp_path):
    e = WorkflowEngine(tmp_path, use_langgraph=False)
    bad = ["calculate_metrics", "retrieve_documents", "verify_evidence", "save_report", "request_approval", "answer"]
    with pytest.raises(PlanRejectedError):
        e.start(request("unsafe-write-01", "report", report_id="rep-1", dry_run=False),
                role="manager", proposed_plan=bad)
    s = e.start(request("safe-write-01", "report", report_id="rep-2", dry_run=False), role="manager")
    assert s.status == "awaiting_approval"
    assert not (tmp_path / "outputs" / "reports" / "rep-2.json").exists()
    e.store.close()


def test_rejected_checkpoint_plan_blocks_approval_and_write(tmp_path):
    e = WorkflowEngine(tmp_path, use_langgraph=False)
    s = e.start(request("checkpoint-01", "report", report_id="rep-3", dry_run=False), role="manager")
    assert s.status == "awaiting_approval"
    tampered = e.store.load(s.request_id)
    tampered.plan.remove("request_approval")
    e.store.save(tampered)
    with pytest.raises(ApprovalError, match="plan"):
        e.decide(s.request_id, reviewer="local-reviewer", approved=True, reason="Local approval sample")
    with pytest.raises(ApprovalError, match="plan"):
        e.resume(s.request_id)
    assert not (tmp_path / "outputs" / "reports" / "rep-3.json").exists()
    e.store.close()


def test_rejected_cursor_blocks_resume(tmp_path):
    e = WorkflowEngine(tmp_path, use_langgraph=False)
    s = e.start(request("checkpoint-02", "report", report_id="rep-4", dry_run=False), role="manager")
    tampered = e.store.load(s.request_id)
    tampered.step_index = 999
    e.store.save(tampered)
    with pytest.raises(ApprovalError, match="cursor"):
        e.resume(s.request_id)
    e.store.close()


def broken_registry(root, counter):
    reg = make_cp2_registry(root)
    def permanently_down(values):
        counter.append(1)
        raise ConnectionError("Synthetic read tool failed")
    reg._tools["calculate_metrics"] = ToolDefinition(permanently_down, MetricsInput, MetricsOutput, True)
    return reg


def test_read_circuit_breaks_after_two_failures_and_blocks_next_request(tmp_path):
    calls = []
    gate = ReadToolCircuit(max_consecutive_failures=2)
    e = WorkflowEngine(tmp_path, registry=broken_registry(tmp_path, calls),
                       use_langgraph=False, read_circuit=gate)
    first = e.start(request("breaker-a-01", "metrics"))
    assert first.status == "failed" and len(calls) == 2
    assert gate.snapshot()["calculate_metrics"] == {"consecutive_failures": 2, "blocked": True}
    second = e.start(request("breaker-b-01", "metrics"))
    assert second.status == "failed" and second.error == "Read-only tool circuit is open"
    assert [x["status"] for x in second.tool_calls] == ["blocked"]
    assert len(calls) == 2
    e.store.close()


def test_blocked_tool_does_not_disable_unrelated_tool(tmp_path):
    calls = []
    gate = ReadToolCircuit(max_consecutive_failures=1)
    e = WorkflowEngine(tmp_path, registry=broken_registry(tmp_path, calls),
                       use_langgraph=False, read_circuit=gate)
    e.start(request("breaker-a-02", "metrics"))
    ok = e.start(request("breaker-b-02", "retrieval"))
    assert ok.status == "success" and [e["tool"] for e in ok.evidence] == ["retrieve_documents"]
    assert len(calls) == 1
    e.store.close()


def test_explicit_reset_allows_diagnostic_retry(tmp_path):
    calls = []
    gate = ReadToolCircuit(max_consecutive_failures=1)
    e = WorkflowEngine(tmp_path, registry=broken_registry(tmp_path, calls),
                       use_langgraph=False, read_circuit=gate)
    e.start(request("breaker-a-03", "metrics"))
    assert not gate.allows("calculate_metrics")
    gate.reset("calculate_metrics")
    assert gate.allows("calculate_metrics")
    e.start(request("breaker-b-03", "metrics"))
    assert len(calls) == 2
    e.store.close()


def test_success_clears_consecutive_failures(tmp_path):
    gate = ReadToolCircuit(max_consecutive_failures=3)
    gate.failure("calculate_metrics")
    assert gate.snapshot()["calculate_metrics"]["consecutive_failures"] == 1
    e = WorkflowEngine(tmp_path, use_langgraph=False, read_circuit=gate)
    assert e.start(request("success-01", "metrics")).status == "success"
    assert gate.snapshot() == {}
    e.store.close()


@pytest.mark.parametrize("invalid", [0, 11, True, False, -1, 1.5, "3", None])
def test_invalid_circuit_policy_rejected(invalid):
    with pytest.raises(ValueError):
        ReadToolCircuit(max_consecutive_failures=invalid)


def test_circuit_is_opt_in_and_does_not_modify_default_path(tmp_path):
    e = WorkflowEngine(tmp_path, use_langgraph=False)
    assert e.read_circuit is None
    assert e.start(request("legacy-default-01")).status == "success"
    e.store.close()


def test_no_generated_text_or_environment_fields_in_circuit_snapshot():
    gate = ReadToolCircuit(max_consecutive_failures=1)
    gate.failure("calculate_metrics")
    view = gate.snapshot()
    assert list(view) == ["calculate_metrics"]
    assert set(view["calculate_metrics"]) == {"consecutive_failures", "blocked"}
