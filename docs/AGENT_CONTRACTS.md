# Project 14 — Agent and Tool Contracts (CP1 frozen baseline)

**CP1 is a one-tool deterministic baseline, not a deployed or fully agentic workflow.** No network, model calls, writes, arbitrary code, shell commands, SQL or external accounts are available through the baseline.

## Unit of analysis and task classes

One incoming request is one evaluation unit; the CP1 baseline accepts a task class plus validated argument object. The maximum is **one registered read-only tool invocation** per request. `metrics` uses the `calculate_metrics` tool with 1–100 finite values, returning count and mean. `retrieval` uses `retrieve_documents` with a 1–256-character query against three synthetic fixtures; it returns source IDs, titles and exact fixture text. Unknown task classes terminate without a tool call. No sensitive, real employee or external data is permitted.

## Authorized roles and actions

The existing `ROLE_TOOLS` table is an allowlist. The `analyst` role can use CP1 metric and retrieval tools. Unrecognized roles have no permissions. `admin` does not bypass the registered-name requirement. There are no write-capable tools in CP1; attempted registration is rejected. The `ToolRegistry.execute` method is the controlled entrypoint. Its backward-compatible raw `get()` method is not authorized for execution and must not be exposed as a service interface.

## Validation and evidence

Both input and tool output pass strict Pydantic contracts; unknown fields are rejected. Authorization precedes argument handling and execution. The result is canonical-JSON serialized and SHA256-hashed only after successful schema verification. Retrieval source IDs must come from the synthetic corpus. No-evidence retrieval returns `no_evidence` and **no evidence hash**. Text retrieved from fixtures or submitted as search terms remains untrusted data, not instructions.

## Terminal outcomes and error behavior

`success`, `no_evidence`, `unauthorized`, `invalid_input`, `unknown_tool`, `failed`, `unsupported` are the planned baseline vocabulary. Unsupported requests never call tools. Unauthorized requests never call tools. Invalid input or invalid output never produces a verified success claim. Exceptions do not leak raw tool errors into the response. Full workflow status transitions, retries, persistent execution state, human approval, cancellation and resume belong to CP2.

## Human approval policy (future CP2)

Any sensitive, externally visible, destructive, write-capable or high-cost action requires explicitly recorded human authorization before execution; non-idempotent side effects must not be retried blindly. CP1 does not implement such actions or approval nodes.

## Reproducibility

Input fixtures: `data/fixtures/sample_documents.json` and `data/fixtures/sample_metrics.json`, both marked `synthetic-v1`. `scripts/validate_cp1.py` runs local pytest checks and prints four smoke scenario summaries. Python 3.12 is recommended; no LLM credentials are required.
