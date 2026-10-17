import pytest
from fastapi.testclient import TestClient

from agentic_ai.api.main import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTIC_AI_PROJECT_ROOT", str(tmp_path))
    for name in ("ANALYST", "MANAGER", "ADMIN", "APPROVER"):
        monkeypatch.delenv(f"AGENTIC_AI_LOCAL_{name}_TOKEN", raising=False)
    return TestClient(app)


def test_public_health_plan_are_not_execution(client):
    assert client.get("/health").json()["external_actions"] is False
    plan = client.post("/plan", json={"query": "What is the average?"}).json()
    assert plan["executed"] is False and "calculate_metrics" in plan["plan"]


def test_workflow_api_fails_closed_without_configured_token(client):
    req = {"request_id": "apiunauth-001", "task_type": "metrics", "metrics": {"values": [1]}}
    assert client.post("/workflows", json=req).status_code == 401
    assert client.post("/workflows", json=req, headers={"X-Api-Key": "guess"}).status_code == 401


def test_api_authorization_and_approval_separation(client, monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTIC_AI_LOCAL_MANAGER_TOKEN", "local-manager-test-token-123")
    monkeypatch.setenv("AGENTIC_AI_LOCAL_APPROVER_TOKEN", "independent-approver-token-456")
    request = {"request_id": "api-report-001", "task_type": "report", "metrics": {"values": [10,20,30]},
               "retrieval": {"query": "leave policy"}, "report_id": "api-report1", "dry_run": False}
    role_key = {"X-Api-Key": "local-manager-test-token-123"}
    status = client.post("/workflows", json=request, headers=role_key)
    assert status.status_code == 200 and status.json()["status"] == "awaiting_approval"
    assert client.post("/workflows/api-report-001/approval", json={"reviewer": "local-reviewer", "approved": True,
                               "reason": "Approved synthetic only"}, headers=role_key).status_code == 401
    assert not (tmp_path / "outputs" / "reports" / "api-report1.json").exists()
    approval = client.post("/workflows/api-report-001/approval", json={"reviewer": "local-reviewer", "approved": True,
                           "reason": "Approved synthetic only"}, headers={"X-Api-Key": "independent-approver-token-456"})
    assert approval.status_code == 200 and approval.json()["status"] == "success"
    assert (tmp_path / "outputs" / "reports" / "api-report1.json").exists()
    assert client.post("/workflows", json=request, headers=role_key).status_code == 409


def test_api_role_cannot_self_assert_privileges(client, monkeypatch):
    monkeypatch.setenv("AGENTIC_AI_LOCAL_ANALYST_TOKEN", "local-analyst-test-token")
    request = {"request_id": "api-block-001", "task_type": "report", "metrics": {"values": [1]},
               "retrieval": {"query": "leave policy"}, "report_id": "api-blocked", "dry_run": False,
               "role": "admin"}
    assert client.post("/workflows", json=request, headers={"X-Api-Key": "local-analyst-test-token"}).status_code == 422


def test_api_approval_token_must_differ_from_caller_token(client, monkeypatch):
    monkeypatch.setenv("AGENTIC_AI_LOCAL_MANAGER_TOKEN", "same-local-token")
    monkeypatch.setenv("AGENTIC_AI_LOCAL_APPROVER_TOKEN", "same-local-token")
    result = client.post("/workflows/anything/approval", json={"reviewer": "test-reviewer", "approved": True,
                         "reason": "Approved synthetic action"}, headers={"X-Api-Key": "same-local-token"})
    assert result.status_code == 403


def test_api_different_role_cannot_read_other_workflow(client, monkeypatch):
    monkeypatch.setenv("AGENTIC_AI_LOCAL_MANAGER_TOKEN", "manager-test-token")
    monkeypatch.setenv("AGENTIC_AI_LOCAL_ANALYST_TOKEN", "analyst-test-token")
    req = {"request_id": "access-000001", "task_type": "metrics", "metrics": {"values": [5,10]}}
    assert client.post("/workflows", json=req, headers={"X-Api-Key": "manager-test-token"}).status_code == 200
    assert client.get("/workflows/access-000001", headers={"X-Api-Key": "analyst-test-token"}).status_code == 403
