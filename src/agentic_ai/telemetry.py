"""Minimal CP3 allowlisted audit metadata; no prompts, records, tokens or raw tool results.

Traces are diagnostic metadata, not immutable security/audit logs and not
cryptographically authenticated against an actor who can modify local SQLite.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

ALLOWED_NODES = frozenset({
    "calculate_metrics", "retrieve_documents", "verify_evidence",
    "request_approval", "save_report", "answer",
})
ALLOWED_STATES = frozenset({
    "running", "awaiting_approval", "rejected", "success", "no_evidence",
    "invalid", "unauthorized", "failed", "dry_run",
})


def trace_id_for(request_id: str) -> str:
    """Stable opaque correlation ID. Does not incorporate input payloads."""
    return hashlib.sha256(("cp3-trace-v1:" + request_id).encode("utf-8")).hexdigest()[:20]


def redact_event(*, node: str, before: str, after: str, step_index: int,
                 elapsed_ns: int, evidence_count: int, tool_call_count: int) -> dict[str, Any]:
    """Allowlist fields/values so untrusted text can never become log content."""
    return {
        "node": node if node in ALLOWED_NODES else "unrecognized",
        "status_before": before if before in ALLOWED_STATES else "invalid",
        "status_after": after if after in ALLOWED_STATES else "invalid",
        "step_index": max(0, int(step_index)),
        "elapsed_ms": round(max(0, elapsed_ns) / 1_000_000, 3),
        "evidence_count": max(0, int(evidence_count)),
        "tool_call_count": max(0, int(tool_call_count)),
    }


def percentile_95(numbers: list[float]) -> float | None:
    """Nearest-rank p95. For small N, report N explicitly."""
    if not numbers:
        return None
    ranked = sorted(numbers)
    rank = (95 * len(ranked) + 99) // 100
    return round(ranked[min(rank - 1, len(ranked) - 1)], 3)


def monotonic_ns() -> int:
    return time.perf_counter_ns()
