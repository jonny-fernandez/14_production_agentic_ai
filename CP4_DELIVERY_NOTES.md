# CP4 audit preparation (not GitHub publication)

**First:** preserve any local outputs you want; the validator refreshes CP3 report/trace JSONs under ignored `outputs/`. No real API calls or remote writes.

Extract this consolidated ZIP into `C:\Users\Jonny Fernandez\Documents\github files` with `-Force`. It preserves your local `.venv` and existing `.env`; original `.env` content is not included in the ZIP. The audit detects its presence without reading it. Revoke/rotate the original exposed credential outside this workflow.

Run ` .\.venv\Scripts\python.exe scripts\validate_cp4.py ` from the project directory. The command runs full tests and re-evaluates 23 pinned synthetic LangGraph scenarios, then audits the output and writes `outputs/cp4_prepublication_audit.json`.

Share the PowerShell result and audit JSON. Do not push to GitHub yet. Screenshots and an actual Word screenshot handoff are required first; see `docs/CP4_SCREENSHOT_CAPTURE.md`. Github CI is a candidate only until proven successful.
