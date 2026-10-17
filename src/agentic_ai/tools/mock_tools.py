"""Deterministic read-only tools backed by small explicitly synthetic fixtures."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

_FIXTURE = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "sample_documents.json"
_STOP = {"a", "an", "and", "are", "can", "do", "does", "for", "in", "is", "me", "of", "on", "or", "say", "the", "to", "what"}


def calculate_metrics(values: list[float]) -> dict[str, float | int]:
    """Compute a sample mean; only call through the validating ToolRegistry."""
    if not values or len(values) > 100 or any(not math.isfinite(x) for x in values):
        raise ValueError("Metrics require 1-100 finite values.")
    result = math.fsum(values) / len(values)
    if not math.isfinite(result):
        raise ValueError("Metrics result is non-finite.")
    return {"count": len(values), "mean": result}


def retrieve_documents(query: str) -> list[dict[str, str]]:
    """Exact finite corpus, no dynamic source text and no arbitrary file access."""
    dataset = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    if dataset.get("fixture_version") != "synthetic-v1":
        raise ValueError("Unknown fixture version.")
    terms = set(re.findall(r"[a-z0-9]+", query.lower())) - _STOP
    if not terms:
        return []
    ranked: list[tuple[int, str, dict[str, str]]] = []
    for document in dataset["documents"]:
        indexed_terms = set(re.findall(r"[a-z0-9]+", (document["title"] + " " + document["text"]).lower()))
        hits = len(terms & indexed_terms)
        if hits:
            ranked.append((-hits, document["source_id"], document))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [doc for _, _, doc in ranked[:10]]


def retrieval_adapter(query: str) -> dict:
    return {"documents": retrieve_documents(query), "fixture_version": "synthetic-v1"}
