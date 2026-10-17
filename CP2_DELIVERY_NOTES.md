# Project 14 — CP2 consolidated candidate

Prepared October 16, 2026. This package **extends the validated CP1 starter**. It is not a new repository. CP2 remains **pending the owner's Windows validation**.

## Actual implemented changes

- Added deterministic multi-step workflow engine with a finite execution budget, and a compiled LangGraph state graph when LangGraph is installed. An equivalent native runner permits isolated unit tests when the package is unavailable; it does **not** count as passing the LangGraph acceptance gate.
- Added two-tool `analysis` workflow (`calculate_metrics` + `retrieve_documents`) and optional local `report` workflow (`calculate_metrics`, `retrieve_documents`, verified evidence, human approval, `save_report`).
- Added SQLite checkpoints with duplicate request denial, optimistic revision checks, approval pause/resume, and persisted step-level records.
- Added strict report schemas, safe fixed output folder, exclusive immutable file creation, verified write contents, and optional human approval (no external operations).
- Extended tool registry with opt-in write-tool registration and mandatory approval at execution; CP1 registry continues to reject writes by default.
- Added bounded retries for read-only tools only; no automatic retry of uncertain writes.
- Added localhost-only FastAPI demo with fail-closed execution/approval credentials; `/health` and `/plan` do not execute tools. All configured tokens must be unique. Bind API to **127.0.0.1**, not public IP.
- Added regression coverage for positive multi-tool paths, authorization, malicious IDs, prompt-injection-shaped requests, missing evidence, manual denials, approval, durable resume, collisions, uncertain writes, role isolation and checkpoint revision conflicts.

## Install (existing Windows project)

The ZIP contains a single root folder named `14_production_agentic_ai`. Extract its contents into your existing portfolio parent folder. Existing `.venv`, `.env`, local SQLite files, and generated output files are **not** included or removed.

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\Project14_CP2_Orchestration.zip" -DestinationPath "$env:USERPROFILE\Documents\github files" -Force
Set-Location "$env:USERPROFILE\Documents\github files\14_production_agentic_ai"
.\.venv\Scripts\python.exe -m pip install -r requirements-cp2.txt
.\.venv\Scripts\python.exe scripts\validate_cp2.py
```

Send the validation output before calling CP2 complete. The validation script **requires a usable LangGraph installation**, runs all tests, and then exercises a real compiled graph with synthetic scenarios. It will fail rather than silently treat native fallback as graph success.

## Safety and limitations

- Never archive or share existing `.env`. Revoke/rotate any real credential previously packaged in the original starter ZIP. The CP2 ZIP contains no `.env` or key.
- The API role is bound to a locally configured execution token; an independent approval token is required for report writes. These are demonstration controls, **not production identity verification, MFA, SSO, TLS, cloud deployment or multi-user protection**.
- All outputs are local, synthetic demonstration artifacts under `outputs/reports/`. Approval represents the presence of a separately configured local reviewer credential, not verified corporate human identity.
- SQLite storage and `WorkflowEngine` are single-process demonstration facilities. Full cross-worker locking, distributed persistence, cancellation and recovery from partially-written files require further engineering. Never re-run an uncertain write automatically.
- The fixed fixture corpus is intentionally small. Do not use sensitive employer or personal data as inputs. Neither general LLM prompting nor live tools run by default.
- Optional original adapter stubs remain unimplemented; do not claim live SQL, RAG, ML models, OpenAI inference or cloud integration.
- CP3 will evaluate broader adversarial scenarios, observability and performance budgets; CP4 covers screenshots, final documentation, GitHub, and resume evidence.

## Author-side validation

The code author observed **62 tests passed, 1 skipped** on a Linux sandbox where LangGraph could not be installed because package installation had no network access. LangGraph graph tests and the complete Windows validation **have not yet passed**. Do not claim CP2 is complete until the owner's output is verified.
