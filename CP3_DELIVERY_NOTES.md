# Project 14 — CP3 consolidated candidate

Extends the **Windows-validated CP2 package (62 tests passed, 1 skipped, plus LangGraph smoke)**. This ZIP includes the corrected Windows symlink test. No `.env`, credential, venv, cache, or generated reports are bundled.

## Changes

- Added allowlisted, redacted per-step telemetry with SHA256-derived trace IDs and wall-clock execution measurements, included in SQLite and safe API response metadata.
- Hardened evidence verification to require **complete ordered evidence** for every already-executed tool plus validated output schema and SHA256 match. Synthetic retrieval source IDs are now restricted to three known fixture IDs.
- Added a SHA256-frozen 23-scenario security/reliability evaluation covering positive tasks, adversarial requests and untrusted tool outputs, authorization, approval replay, deterministic resume/retry and uncertain write handling.
- Added machine-measured JSON evaluation report and redacted JSONL traces generated when the user runs the CP3 validation command.
- Added CP3 regression tests and focused documentation on explicit limitations; no unrelated starter modules or repository layout replaced.

## Install / validate on Windows

Download ZIP into Downloads, extract into the existing project parent folder; then run:

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\Project14_CP3_Evaluation.zip" -DestinationPath "$env:USERPROFILE\Documents\github files" -Force
Set-Location "$env:USERPROFILE\Documents\github files\14_production_agentic_ai"
.\.venv\Scripts\python.exe scripts\validate_cp3.py
```

No new dependency installation is necessary beyond completed CP2. Send final PowerShell output and the generated `outputs/cp3_evaluation_report.json` for review. CP3 is **not complete** until the Windows LangGraph run is reviewed.

## Known honest boundary

Locally measured deterministic synthetic tests do not establish general-purpose agent reliability, live AI-model accuracy, production security or cost. No paid API, employer data, real external accounts or hosted deployment are involved. The previously discovered populated `.env` from the original starter is **not** included and must be excluded from archives; rotate any exposed original key. Extraction will not delete your existing local `.env`.
