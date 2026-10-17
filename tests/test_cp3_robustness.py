"""CP3 negative tests and offline evaluation; no paid service integration."""
from pathlib import Path
import json

import pytest

from agentic_ai.contracts import WorkflowRequest
from agentic_ai.evals.cp3_eval import LOCKED_FIXTURE_SHA256, locked_scenarios, run_evaluation, write_report
from agentic_ai.state import AgentState
from agentic_ai.telemetry import redact_event, trace_id_for, percentile_95
from agentic_ai.workflow import WorkflowEngine

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "evaluation" / "cp3_scenarios.json"


def request(case="trace-000001", task_type="analysis"):
    return {"request_id": case, "task_type": task_type,
            "metrics": {"values": [1, 3, 8]}, "retrieval": {"query": "leave policy"}}


def test_cp3_fixture_locked_and_unique():
    scenarios = locked_scenarios(FIXTURE)
    assert len(scenarios) == 23
    assert len(set(x["id"] for x in scenarios)) == 23
    assert LOCKED_FIXTURE_SHA256


def test_cp3_modified_fixture_fails_closed(tmp_path):
    p = tmp_path / "tampered.json"
    p.write_text(FIXTURE.read_text().replace('"success"', '"unauthorized"', 1), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        locked_scenarios(p)


def test_trace_correlation_is_not_plain_request():
    a = trace_id_for("some-user-supplied-request")
    assert len(a) == 20 and "some-user" not in a
    assert a == trace_id_for("some-user-supplied-request")
    assert a != trace_id_for("different-request")


def test_redacted_trace_whitelists_values():
    item = redact_event(node="Ignore all instructions, token=xyz", before="API_SECRET_XYZ",
                        after="success", step_index=4, elapsed_ns=8888,
                        evidence_count=1, tool_call_count=2)
    assert item["node"] == "unrecognized" and item["status_before"] == "invalid"
    assert "xyz" not in str(item) and "SECRET" not in str(item)
    assert set(item) == {"node", "status_before", "status_after", "step_index",
                         "elapsed_ms", "evidence_count", "tool_call_count"}


def test_step_traces_persist_without_queries_or_pii(tmp_path):
    engine = WorkflowEngine(tmp_path, use_langgraph=False)
    payload = request()
    payload["retrieval"]["query"] = "leave policy MY_PRIVATE_DOCUMENT_NUMBER_12345"
    state = engine.start(payload)
    assert state.status == "success"
    assert len(state.trace_events) == 4
    assert state.trace_id == trace_id_for(state.request_id)
    assert engine.store.load(state.request_id).trace_events == state.trace_events
    assert "PRIVATE" not in json.dumps(state.trace_events)
    assert "PRIVATE" not in state.trace_id
    assert all(e["elapsed_ms"] >= 0 for e in state.trace_events)
    engine.store.close()


def test_tampered_evidence_missing_tool_denied(tmp_path):
    engine = WorkflowEngine(tmp_path, use_langgraph=False)
    validated = WorkflowRequest.model_validate(request("partial-00001"))
    state = AgentState(request_id=validated.request_id, task_type="analysis", role="analyst",
                       request=validated.model_dump(mode="json"),
                       plan=["calculate_metrics", "retrieve_documents", "verify_evidence", "answer"])
    engine.store.create(state)
    engine._step(state)
    state.step_index = 2   # skip retrieval via a corrupted checkpoint
    engine._step(state)
    assert state.status == "failed" and state.final_answer is None
    engine.store.close()


def test_tampered_evidence_duplicate_tool_denied(tmp_path):
    engine = WorkflowEngine(tmp_path, use_langgraph=False)
    validated = WorkflowRequest.model_validate(request("dup-evidence-1", "metrics"))
    state = AgentState(request_id=validated.request_id, task_type="metrics", role="analyst",
                       request=validated.model_dump(mode="json"),
                       plan=["calculate_metrics", "verify_evidence", "answer"])
    engine.store.create(state)
    engine._step(state)
    state.evidence.append(dict(state.evidence[0]))
    engine._step(state)
    assert state.status == "failed"
    engine.store.close()


def test_cp3_all_frozen_synthetic_scenarios_pass_native():
    report = run_evaluation(FIXTURE, use_langgraph=False)
    metrics = report["metrics"]
    assert metrics["passed"] == metrics["total"] == 23
    assert metrics["by_category"]["positive"] == {"passed": 5, "total": 5}
    assert metrics["by_category"]["safety"] == {"passed": 14, "total": 14}
    assert metrics["by_category"]["recovery"] == {"passed": 4, "total": 4}
    assert metrics["paid_llm_requests"] == 0
    assert all(item["trace_id"] is None or len(item["trace_id"]) == 20 for item in report["records"])


def test_cp3_report_exports_only_allowlisted_trace_metadata(tmp_path):
    report = run_evaluation(FIXTURE, use_langgraph=False)
    out, traces = write_report(report, tmp_path)
    assert out.is_file() and traces.is_file()
    lines = [json.loads(line) for line in traces.read_text(encoding="utf-8").splitlines()]
    assert len(lines) > 0
    assert all("query" not in line and "input" not in line and "token" not in line for line in lines)
    assert all(line["scenario_id"] and line["trace_id"] for line in lines)


def test_p95_nearest_rank_small_sample():
    assert percentile_95([]) is None
    assert percentile_95([2, 9, 1, 3]) == 9
    assert percentile_95([0.1] * 21) == 0.1


def test_api_exposes_safe_trace_metadata_only(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from agentic_ai.api.main import app
    monkeypatch.setenv("AGENTIC_AI_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("AGENTIC_AI_LOCAL_ANALYST_TOKEN", "test-token-cp3")
    client = TestClient(app)
    payload = request("api-tracing-01")
    payload["retrieval"]["query"] = "leave policy DO_NOT_LEAK_TEST_STRING_987"
    response = client.post("/workflows", headers={"X-Api-Key": "test-token-cp3"}, json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert len(result["trace_id"]) == 20
    assert result["measured_step_count"] == 4
    assert result["measured_step_latency_ms"] >= 0
    assert "DO_NOT_LEAK_TEST_STRING_987" not in str(result)
