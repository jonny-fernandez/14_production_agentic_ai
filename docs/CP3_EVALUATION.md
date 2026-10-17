# CP3 — Security, evaluation, and observability (local, synthetic)

## Freeze and acceptance

- Unit: **one named synthetic workflow scenario** (`scenario_id`) from `data/evaluation/cp3_scenarios.json`.
- The complete raw file is SHA256 pinned in `agentic_ai.evals.cp3_eval.LOCKED_FIXTURE_SHA256`. Changes must be deliberately versioned and the hash updated **before** rerunning; don't patch gold standards in response to results.
- CP3 gate: all existing tests pass, the compiled LangGraph graph executes on Windows, all **23/23** scenarios match their predefined results, and the JSON report is generated under ignored `outputs/`.
- Groups: 5 positive, 14 safety/abuse and 4 recovery scenarios. Scores are exact observed-status matches, not independent estimates of real-world attack prevention.
- Developer-visible fixture and deterministic rule-based workflows mean this is a **development regression set**, NOT a blinded/held-out test or evidence of general-purpose agent reliability.

## Covered behaviors

- Metrics, retrieval, analysis, dry-run and independently approved local report writes.
- Denied/rejected writes, invalid roles, invalid input and path traversal, duplicate requests and approval replay.
- Empty retrieval evidence, unregistered tools, schema-invalid tool results and unapproved source IDs.
- Injection-shaped user search text and hostile retrieved document text (must never cause execution or leak in final answer/trace).
- SQLite approval pause/restart/resume; bounded transient-read retries and persistent-read failures; write faults never automatically retried.
- Missing/duplicate/altered checkpoint evidence checks in the automated test suite.
- The existing Windows symlink security regression is skipped if non-elevated Windows denies symlink creation (WinError 1314); this does **not** demonstrate that symlink protection was verified on that machine.

## Observability and metrics

- `trace_id` is a stable SHA256-derived correlation value (20 lowercase hex chars), not an authentication token or cryptographically authenticated record.
- Step traces include only allowlisted node/status, local monotonic elapsed milliseconds, step index and counts. They **do not** contain query text, retrieved documents, credentials, tool arguments, model prompts or raw results. They are saved to the SQLite demo state and can be exported from evaluation under `outputs/cp3_redacted_traces.jsonl`.
- `outputs/cp3_evaluation_report.json` contains observed/expected scenario outcomes, trace IDs, source fixture SHA256, tool attempt counts, and actual measured mean/p95 **local scenario elapsed time**. P95 is nearest-rank using 23 observations; latency is machine-specific and includes scenario setup. Do not compare across computers.
- API responses disclose only trace ID and aggregate measured step counts/latency; never raw trace text or stored inputs.
- Paid LLM request/token count is zero because the benchmark is deterministic and does not call any hosted model. API billing recorded as $0, excluding local compute, engineering, hosting, licensing and other costs.
- The evaluator does **not** measure a learned intent router, live provider accuracy, general LLM reasoning, secure execution of arbitrary code, real operator authentication, network timeouts, or production workload throughput. No success should be claimed for those areas.

## Windows validation

Run from `14_production_agentic_ai` with its existing isolated Python 3.12 `.venv`:

```powershell
.\.venv\Scripts\python.exe scripts\validate_cp3.py
```

The command runs the complete test suite and requires actual LangGraph to be importable; it then runs all 23 frozen scenarios **through the compiled LangGraph runner**. It uses synthetic files and local temporary SQLite databases, with no external services or paid calls. On a failed test/scenario it exits nonzero and CP3 remains open.

## Security and operational limitations

The system has a bounded step/attempt count, but **no hard per-tool wall-clock timeout or external process sandbox**; only preapproved local synthetic tools may execute. CP3 traces are sanitized diagnostic metadata, **not** signed append-only audit records. Persisted SQLite states can contain raw provided queries/metrics and synthetic document bodies and must not be populated with PII or real company data. An actor with filesystem/SQLite write access may modify both evidence and stored hashes; hashes are not a substitute for an authenticated provenance service. Runtime has no enterprise identity, network isolation, distributed locks, production-grade concurrency, cloud hosting, real service connectors, or comprehensive prompt-injection security certification. The write sink is for a synthetic local file only.

CP4 remains responsible for final audit, screenshot evidence, final CI and GitHub publication. In particular, don't claim these local synthetic results represent a public live deployment.

## CP4 terminology clarification

Prior CP3 report records named the number of failed tool-attempt records `retried_tools`; that name was misleading. The CP4 candidate uses `failed_tool_attempts` for the same count. An uncertain write can fail once without automatic retry. The CP3 pinned fixture and expectations remain unchanged.
