# Project 14 — Evaluation Plan

## Locked CP1 acceptance checks (before user-side execution)

- Each evaluation case is one tool/task request plus its expected terminal outcome.
- Test count and pass rate come **only** from actual pytest output, never from this plan.
- Positive cases: finite arithmetic with known exact fixture mean; retrieval limited to approved synthetic source IDs; determinism of output and SHA256 digest.
- Negative cases: invalid data shape/range, unknown fields, NaN/infinity, oversized values/queries, unknown task/tool, denied role, write-tool registration, malformed tool result, and injected instructions in retrieval query.
- Safety gate: no unauthorized tool execution, no success when evidence absent or invalid, no API spend, no network, no secrets committed.
- Failure gate: if any test fails, CP1 remains pending; attach traceback and fix before proceeding.

## CP2/CP3 reserved metrics (NOT currently measured)

Intent classification accuracy, plan/tool/argument quality, end-to-end task success, task budget/loop exhaustion, idempotent recovery, human approval behavior, prompt-injection success/block rate, unsupported claims, unnecessary tool calls, latency distribution (mean and P95), token usage and monetary costs. Establish frozen datasets, gold standards, metric definitions and sample sizes before held-out evaluations. Use deterministic/mock adapters by default; real model requests are opt-in only.

## Result integrity

Every future result record should include tool evidence/source IDs, model/provider mode, fixture version, scenario ID, execution status, and SHA256 where appropriate. Do not portray unit tests, synthetic demonstrations, or local validation as evidence of production readiness or hosted deployment.

## CP3 pinned synthetic evaluation (candidate; October 2026)

The separate `docs/CP3_EVALUATION.md` documents the newly implemented 23-case pinned local regression benchmark and its exact metrics. This is a development scenario test, **not** a real-world representative held-out test. The required Windows execution is `scripts/validate_cp3.py` and is pending review. Original CP2/CP3 planned model/router quality metrics remain **not measured** because no LLM planner or learned router is exercised. Avoid retroactively describing the development test set as held-out evaluation.
