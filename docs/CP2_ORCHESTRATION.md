# CP2 execution and safety design

## Concrete task classes

| Task | Steps | Writes? | Expected terminal state |
|---|---|---|---|
| `metrics` | validated metrics -> evidence hash -> answer | No | `success` or bounded failure |
| `retrieval` | approved synthetic corpus search -> evidence hash -> answer | No | `success` or `no_evidence` |
| `analysis` | metrics -> retrieval -> hash verification -> answer | No | `success` or bounded failure |
| `report` / dry run | metrics -> retrieval -> verify -> preview | No | `dry_run` or bounded failure |
| `report` / approved | metrics -> retrieval -> verify -> pause approval -> immutable local report -> answer | One local file | `awaiting_approval`, `rejected`, or `success` after approval |

The unit of analysis is one `request_id`. Duplicate IDs are rejected before any tool re-execution. A `report_id` names an immutable local synthetic JSON artifact, never a user-supplied path. The allowed set of tools, allowed roles and permitted plan shape are deterministic. Retrieved text, user queries and LLM messages cannot supply executable commands or change registered tool names.

## State and graph

`WorkflowEngine` creates a `StateGraph` when LangGraph is available. Each graph iteration runs one controlled step, persists the state to SQLite with optimistic revision matching and routes either to the next step or to a terminal/pause state. The same pure step implementation has a fallback for CPU-only offline unit tests; acceptance requires the LangGraph path to execute locally. There are at most eight planned steps per workflow and at most two attempts per read-only tool by default. Write tools are never retried after an uncertain failure.

Persisted fields include the task, trusted role, plan/step cursor, validated input, attempted tools, verified outputs, output hashes, review decision, outcome and bounded error message. Do not use personal identifiers or confidential data for this synthetic demo.

## Approval process

For report workflows with `dry_run=false`, the graph pauses before `save_report` and returns `awaiting_approval`. A locally trusted reviewer records approval or rejection and reason; the approved resume verifies evidence again. Denial has no local write side effect. Direct write execution requires both manager/admin permission and `approval_granted`, with a separately configured API approver token. Dry runs produce no report file.

This is an offline *simulation* of human approval, not proof of a verified person's identity in a production organization.

## Evidence and output control

Strict Pydantic schemas validate tool inputs/outputs. Canonical JSON SHA256 is calculated only after successful validation. Reports include the verified sample mean/count, approved synthetic source IDs and their two evidence digests. Each file uses exclusive creation and is checked after writing; an existing same-content file is recognized, a conflicting artifact is rejected. Missing retrieval evidence stops execution before report or final answer.

The system does not synthesize policy interpretations or business facts from retrieved text: it reports only retrieved source IDs and measured synthetic numbers. Secrets, arbitrary files, shell, live database access and network access are not registered tools.

## API configuration (optional)

`/plan` and `/health` are intentionally informational and public **on the local host**. POST `/workflows` accepts validated requests and gets the role from a server-side environment token, not the JSON body; GET `/workflows/{id}` is restricted to the workflow role/admin. POST `/workflows/{id}/approval` needs a distinct local approver credential. All execution endpoints deny access if tokens are unset. Tokens belong in your process environment, not Git-tracked files or screenshots.

For demonstration only, launch with `uvicorn agentic_ai.api.main:app --host 127.0.0.1 --port 8000` and `PYTHONPATH=src` in PowerShell. Do not use `--host 0.0.0.0` or deploy this demo publicly. No external API calls are required.

## Known limitations / remaining work

- No general LLM/agent reasoning, external live services or actual enterprise identity integration.
- No distributed locks, durable approval identity/signatures, cancel-in-flight or at-least-once distributed execution semantics.
- SQLite state rows may contain caller-provided numeric values and query text; only synthetic public inputs should be used.
- No production grade logging, redaction evaluation, cost estimation or adversarial fixture benchmarks yet; these are CP3 tasks.
- No Github CI/deployment verification or final screenshot evidence yet; these are CP4 tasks.
