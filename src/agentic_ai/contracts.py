"""CP1 read-only contracts. No model output is trusted as a tool argument or proof."""
from __future__ import annotations

from enum import Enum
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class MetricsInput(ClosedModel):
    values: list[FiniteFloat] = Field(min_length=1, max_length=100)


class MetricsOutput(ClosedModel):
    count: int = Field(ge=1, le=100)
    mean: FiniteFloat


class RetrievalInput(ClosedModel):
    query: str = Field(min_length=1, max_length=256)

    @field_validator("query")
    @classmethod
    def require_meaningful_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("The query must not consist only of whitespace.")
        return value


class SourceRecord(ClosedModel):
    source_id: Literal["SYNTH-DOC-001", "SYNTH-DOC-002", "SYNTH-DOC-003"]
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)


class RetrievalOutput(ClosedModel):
    documents: list[SourceRecord] = Field(max_length=10)
    fixture_version: Literal["synthetic-v1"]


class Outcome(str, Enum):
    SUCCESS = "success"
    NO_EVIDENCE = "no_evidence"
    UNAUTHORIZED = "unauthorized"
    INVALID_INPUT = "invalid_input"
    UNKNOWN_TOOL = "unknown_tool"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class BaselineResult(ClosedModel):
    task_type: Literal["metrics", "retrieval", "unsupported"]
    status: Outcome
    selected_tool: str | None = None
    tool_output: dict | None = None
    evidence_sha256: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    answer: str

# CP2: Strict request envelope. The caller's role is supplied by a trusted
# local execution context, never inferred from retrieved text or an LLM.
class WorkflowRequest(ClosedModel):
    request_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{6,64}$", max_length=64)
    task_type: Literal["metrics", "retrieval", "analysis", "report"]
    metrics: MetricsInput | None = None
    retrieval: RetrievalInput | None = None
    report_id: str | None = Field(default=None, pattern=r"^[a-z0-9_-]{4,48}$")
    dry_run: bool = True

    @field_validator("request_id")
    @classmethod
    def check_request_id(cls, value: str) -> str:
        if re.fullmatch(r"[a-zA-Z0-9_-]{6,64}", value) is None:
            raise ValueError("Unsafe request ID")
        return value

    @field_validator("report_id")
    @classmethod
    def check_report_id(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[a-z0-9_-]{4,48}", value) is None:
            raise ValueError("Unsafe report ID")
        return value

    @model_validator(mode="after")
    def matching_arguments(self):
        if self.task_type in {"metrics", "analysis", "report"} and self.metrics is None:
            raise ValueError("This workflow requires metrics input.")
        if self.task_type in {"retrieval", "analysis", "report"} and self.retrieval is None:
            raise ValueError("This workflow requires retrieval input.")
        if self.task_type == "report" and self.report_id is None:
            raise ValueError("A report workflow needs a report_id.")
        if self.task_type != "report" and (self.report_id is not None or not self.dry_run):
            raise ValueError("Only report workflows may request a write.")
        return self


class ReportInput(ClosedModel):
    report_id: str = Field(pattern=r"^[a-z0-9_-]{4,48}$")

    @field_validator("report_id")
    @classmethod
    def check_report_id(cls, value: str) -> str:
        if re.fullmatch(r"[a-z0-9_-]{4,48}", value) is None:
            raise ValueError("Unsafe report ID")
        return value
    metrics: MetricsOutput
    source_ids: list[str] = Field(min_length=1, max_length=10)
    evidence_sha256: list[str] = Field(min_length=2, max_length=2)

    @field_validator("source_ids")
    @classmethod
    def validate_source_ids(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)) or not all(re.fullmatch(r"SYNTH-DOC-00[1-3]", s) for s in values):
            raise ValueError("Report sources must be unique IDs from the locked synthetic corpus")
        return values

    @field_validator("evidence_sha256")
    @classmethod
    def validate_digests(cls, values: list[str]) -> list[str]:
        if not all(re.fullmatch(r"[a-f0-9]{64}", x) for x in values):
            raise ValueError("Source evidence digests must be complete SHA256 values")
        return values


class ReportOutput(ClosedModel):
    path: str = Field(pattern=r"^outputs/reports/[a-z0-9_-]{4,48}\.json$")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    already_existed: bool
