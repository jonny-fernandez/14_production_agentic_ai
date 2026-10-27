"""Opt-in, offline plan validation and local read-tool circuit breaking.

These controls never use model-generated commands as executable instructions.
The circuit state is in memory, per WorkflowEngine, and is not durable or
shared across workers. No timeouts or production readiness are implied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


CANONICAL_PLANS: dict[str, tuple[str, ...]] = {
    "metrics": ("calculate_metrics", "verify_evidence", "answer"),
    "retrieval": ("retrieve_documents", "verify_evidence", "answer"),
    "analysis": ("calculate_metrics", "retrieve_documents", "verify_evidence", "answer"),
    "report": ("calculate_metrics", "retrieve_documents", "verify_evidence",
               "request_approval", "save_report", "answer"),
}

# Swapping the two independent read-only analysis tools preserves both evidence
# requirements, the verified answer, and all authorization checks. Nothing may
# rearrange approval/write steps or omit any required tool or verification node.
ALTERNATE_ANALYSIS: tuple[str, ...] = (
    "retrieve_documents", "calculate_metrics", "verify_evidence", "answer"
)


class PlanRejectedError(ValueError):
    """A proposed plan fails the trusted, finite execution policy."""


def validated_plan(task_type: str, proposal: Iterable[str] | None = None) -> list[str]:
    if task_type not in CANONICAL_PLANS:
        raise PlanRejectedError("Unsupported task type")
    default = CANONICAL_PLANS[task_type]
    if proposal is None:
        return list(default)
    if not isinstance(proposal, (list, tuple)) or not all(isinstance(x, str) for x in proposal):
        raise PlanRejectedError("A plan must be a list of registered step names")
    candidate = tuple(proposal)
    if candidate == default or (task_type == "analysis" and candidate == ALTERNATE_ANALYSIS):
        return list(candidate)
    raise PlanRejectedError("Proposal violates the tool, evidence, or approval policy")


@dataclass
class ReadToolCircuit:
    """Per-engine, fail-closed blocker for repeated read-tool execution failures.

    This does not add a hard timeout, distributed state, or durable recovery.
    A trusted caller must explicitly reset a circuit after investigation.
    """
    max_consecutive_failures: int = 2
    _failures: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _blocked: set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.max_consecutive_failures, bool) or not isinstance(self.max_consecutive_failures, int) or not 1 <= self.max_consecutive_failures <= 10:
            raise ValueError("max_consecutive_failures must be an integer from 1 through 10")

    def allows(self, tool: str) -> bool:
        return tool not in self._blocked

    def failure(self, tool: str) -> None:
        self._failures[tool] = self._failures.get(tool, 0) + 1
        if self._failures[tool] >= self.max_consecutive_failures:
            self._blocked.add(tool)

    def success(self, tool: str) -> None:
        self._failures.pop(tool, None)

    def reset(self, tool: str) -> None:
        """Administrative reset; do not automatically reset on a timer."""
        self._blocked.discard(tool)
        self._failures.pop(tool, None)

    def snapshot(self) -> dict[str, dict[str, int | bool]]:
        return {name: {"consecutive_failures": self._failures.get(name, 0),
                       "blocked": name in self._blocked}
                for name in sorted(set(self._failures) | self._blocked)}
