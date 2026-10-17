"""Approval decisions are explicit, auditable and never model-generated."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    reviewer: str
    reason: str


def requires_human_approval(sensitive: bool, confidence: float, threshold: float = 0.85) -> bool:
    return sensitive or confidence < threshold
