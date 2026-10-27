# Project 14 — CP3: Fail-closed checkpoint inspection and adversarial evaluation

## Upgrade scope

This additive, opt-in module provides **read-only checkpoint inspection** for the existing deterministic synthetic LangGraph workflow. It does not modify WorkflowEngine, change approval policy, issue tool calls, or replay a workflow. Normal workflow behavior and the frozen 23-scenario evaluation remain unchanged.

The module `agentic_ai.checkpoint_audit` exports:

- `audit_checkpoint(state)`: returns PASS or QUARANTINE with stable reason codes. It checks approved plan shape, cursor bounds, evidence order, SHA-256 consistency and output schema, tool authorization and write-attempt count, approval pause/rejection/dry-run gates, success claims, and trace metadata allowlists.
- `audit_batch(states, max_states=500)`: bounded review with PASS / QUARANTINE / NOT_VERIFIED rollups. An empty batch cannot claim verification.
- `scripts/project14_cp3_adversarial_probe.py`: six independent local negative cases that exercise the inspector. No paid LLM calls or external services.

The review output contains **no raw query, source document, report content, tool argument, token, or credential**. Only a short SHA-256-derived request identifier, status, finding codes and count are returned. The local `.env` is not opened.

## Important limitations

The inspection is **advisory** and does not authorize a resume or approval. Local SHA-256 is a tamper-evidence check for accidental/unsynchronized edits, not authentication of an attacker-controlled SQLite database; someone with local write access can alter a record and its hashes. This package does not provide a durable audit log, process sandbox, distributed consistency, provider-level timeouts, live autonomy, or enterprise production security. Tests use synthetic inputs and rules; they do not establish general prompt-injection resistance. Generated evidence summaries should be described as development validation, not live endpoint screenshots.

## Windows acceptance

From an Administrator Windows PowerShell prompt, to permit the existing symlink regression:

```powershell
$repo = 'C:\Users\Jonny Fernandez\Documents\github files\14_production_agentic_ai'
powershell -NoProfile -ExecutionPolicy Bypass -File "$repo\CP3_Recovery\Project14_CP3_Verify.ps1" -RepoRoot $repo
```

Accept only if **162/162 tests pass**, **0 skipped**, **23/23 frozen scenarios pass through the existing compiled LangGraph validation**, the existing local prepublication audit passes, all **6/6** new adversarial probes pass and evidence integrity checks pass. Do not stage, commit or push until CP4 approval. On failure, upload the newest CP3 evidence ZIP for diagnosis rather than patching the gold-standard fixture.
