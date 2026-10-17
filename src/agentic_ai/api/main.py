"""Local-only FastAPI demo. Authentication is opt-in via environment secrets.

If API tokens are unconfigured all workflow endpoints fail closed. Never expose
this service publicly; it does not implement enterprise SSO or rate limiting.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agentic_ai.contracts import WorkflowRequest
from agentic_ai.router import route_task
from agentic_ai.planner import make_plan
from agentic_ai.state_store import StateConflictError
from agentic_ai.workflow import ApprovalError, WorkflowEngine

app = FastAPI(title="Production Agentic AI Platform (local demo)", version="0.2.0")


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=256)


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reviewer: str = Field(min_length=3, max_length=64)
    approved: bool
    reason: str = Field(min_length=5, max_length=256)


def _role(token: str | None) -> str:
    if not token:
        raise HTTPException(401, "Local API credentials required")
    for role in ("analyst", "manager", "admin"):
        expected = os.getenv(f"AGENTIC_AI_LOCAL_{role.upper()}_TOKEN", "")
        if expected and secrets.compare_digest(token, expected):
            return role
    raise HTTPException(401, "Invalid API credentials")


def _approver(token: str | None) -> None:
    configured = os.getenv("AGENTIC_AI_LOCAL_APPROVER_TOKEN", "")
    if not token or not configured or not secrets.compare_digest(token, configured):
        raise HTTPException(401, "Independent local approval credentials required")
    for role in ("ANALYST", "MANAGER", "ADMIN"):
        candidate = os.getenv(f"AGENTIC_AI_LOCAL_{role}_TOKEN", "")
        if candidate and secrets.compare_digest(candidate, configured):
            raise HTTPException(403, "Approval credential must differ from execution credentials")


def _engine() -> WorkflowEngine:
    project_root = Path(os.getenv("AGENTIC_AI_PROJECT_ROOT") or Path(__file__).resolve().parents[3])
    return WorkflowEngine(project_root)


def _response(state):
    # Deliberately omit input values and source text from the HTTP response.
    return {"request_id": state.request_id, "task_type": state.task_type,
            "status": state.status, "step_index": state.step_index,
            "trace_id": state.trace_id,
            "measured_step_count": len(state.trace_events),
            "measured_step_latency_ms": round(sum(e.get("elapsed_ms", 0) for e in state.trace_events), 3),
            "tool_calls": state.tool_calls,
            "source_ids": [d["source_id"] for e in state.evidence if e["tool"] == "retrieve_documents"
                           for d in e["output"]["documents"]],
            "evidence_sha256": [e["sha256"] for e in state.evidence],
            "final_answer": state.final_answer, "error": state.error}


@app.get("/health")
def health():
    return {"status": "ok", "mode": "local-demo", "external_actions": False}


@app.post("/plan")
def plan(payload: QueryRequest):
    task_type = route_task(payload.query)
    return {"task_type": task_type, "plan": make_plan(task_type), "executed": False}


@app.post("/workflows")
def start_workflow(payload: WorkflowRequest, x_api_key: str | None = Header(default=None)):
    role = _role(x_api_key)
    # Require a separately credentialed approval action for any write request.
    engine = _engine()
    try:
        return _response(engine.start(payload, role=role))
    except StateConflictError:
        raise HTTPException(409, "Request ID already exists") from None
    finally:
        engine.store.close()


@app.get("/workflows/{request_id}")
def get_workflow(request_id: str, x_api_key: str | None = Header(default=None)):
    caller_role = _role(x_api_key)
    engine = _engine()
    try:
        state = engine.store.load(request_id)
        if state is None:
            raise HTTPException(404, "Unknown workflow")
        if caller_role != state.role and caller_role != "admin":
            raise HTTPException(403, "Workflow not visible to this role")
        return _response(state)
    finally:
        engine.store.close()


@app.post("/workflows/{request_id}/approval")
def approve_workflow(request_id: str, payload: ApprovalRequest,
                     x_api_key: str | None = Header(default=None)):
    _approver(x_api_key)
    engine = _engine()
    try:
        try:
            return _response(engine.decide(request_id, reviewer=payload.reviewer,
                                           approved=payload.approved, reason=payload.reason))
        except KeyError:
            raise HTTPException(404, "Unknown workflow") from None
        except ApprovalError:
            raise HTTPException(409, "No approval pending or invalid decision") from None
        except StateConflictError:
            raise HTTPException(409, "Concurrent state modification") from None
    finally:
        engine.store.close()
