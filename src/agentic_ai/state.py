"""Versioned, serializable execution state. No raw secrets or external records."""
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class AgentState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    user_query: str = ""  # kept for compatibility with original starter
    task_type: str = ""
    role: str = ""
    request: dict[str, Any] = Field(default_factory=dict)
    status: Literal["running", "awaiting_approval", "rejected", "success", "no_evidence",
                    "invalid", "unauthorized", "failed", "dry_run"] = "running"
    dry_run: bool = True
    plan: list[str] = Field(default_factory=list)
    step_index: int = 0
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    approval: dict[str, Any] | None = None
    final_answer: str | None = None
    error: str | None = None
    trace_id: str = ""
    trace_events: list[dict[str, Any]] = Field(default_factory=list)
    revision: int = 0
