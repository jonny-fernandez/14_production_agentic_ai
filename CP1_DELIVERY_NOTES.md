# Project 14 — Consolidated CP1 package

Prepared October 16, 2026. This is an upgrade of the existing starter, not a new repository. No existing folder or Git history needs to be replaced.

## Added/updated

- Added: `src/agentic_ai/contracts.py`, `src/agentic_ai/baseline.py`, `src/agentic_ai/providers/mock_provider.py`, `requirements-cp1.txt`, `data/fixtures/sample_documents.json`, `data/fixtures/sample_metrics.json`, `scripts/validate_cp1.py`, `tests/test_cp1_contracts.py`.
- Updated: `src/agentic_ai/tools/mock_tools.py`, `src/agentic_ai/tools/registry.py`, `README.md`, `CHECKPOINTS.md`, `.gitignore`, `docs/AGENT_CONTRACTS.md`, `docs/EVALUATION_PLAN.md`.
- Preserved: original router, planner, roles, SQLite state store, FastAPI skeleton, unimplemented optional adapters, original tests, portfolio roadmap and project rules.
- Excluded: `.env`, Python cache, local `.venv`, any credential values. Existing `.env` files on your PC are **not deleted by ZIP extraction**.

## Installation in existing project (Windows PowerShell)

Place the downloaded ZIP file in `Downloads`, then from any folder:

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\Project14_CP1_Foundation.zip" -DestinationPath "$env:USERPROFILE\Documents\github files" -Force
Set-Location "$env:USERPROFILE\Documents\github files\14_production_agentic_ai"
.\.venv\Scripts\python.exe -m pip install -r requirements-cp1.txt
.\.venv\Scripts\python.exe scripts\validate_cp1.py
```

If your downloaded ZIP is elsewhere, substitute its actual path in `-LiteralPath`. Keep the existing `.venv` intact.

## Safety

Do **not** share your `.env` file. Revoke/rotate any real API key previously included in an uploaded starter ZIP. CP1 validation does not require any API key, network-enabled tool, external account or paid inference. Delete unused local `.env` only after checking whether it contains configuration needed for later phases.

## Verification status

The package author observed 29/29 test passes in a separate Linux Python 3.13 environment; this is **not** proof of execution on the owner's Windows Python 3.12 machine. CP1 remains pending until the owner provides the actual local validation output.
