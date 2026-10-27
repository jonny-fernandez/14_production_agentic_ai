# Project 14 — CP4 Upgrade Release Review (October 2026)

## Release intent

This release publishes the **opt-in CP2 decision/reliability controls** and **read-only CP3 checkpoint integrity auditor**, with test evidence and documentation. The existing synthetic local LangGraph workflow remains deterministic by default. This is not a production deployment, live external-tool integration, or proof of generalized agent safety.

## Verified local results (before GitHub publication)

| Verification | Local evidence | Status |
|---|---|---|
| Existing CP1 baseline | 81 tests, 23/23 scenarios | PASS |
| CP2 complete regression | 113 tests, 23/23 scenarios | PASS |
| CP3 complete regression | 162 tests, 0 failures, 0 skips | PASS, twice |
| Compiled LangGraph frozen evaluation | 23/23: 5 positive, 14 safety, 4 recovery | PASS |
| CP3 checkpoint adversarial probes | 6/6 | PASS |
| CP3 local prepublication audit | No suspicious tracked-secret patterns | PASS with manual review |

Evidence source: Project14_CP3_Evidence_20261027_185920_UTC.zip and Project14_CP3_Evidence_20261027_190001_UTC.zip. Local reports were verified from SHA-256 manifests in the checkpoint audit; reported results are not live GitHub Actions outcomes. Test counts include deterministic synthetic cases; no paid LLM requests.

## What was added

- CP2: trusted plan policy, protection against untrusted plan alteration, and an opt-in local circuit breaker for repeated read-only tool failures.
- CP3: `agentic_ai.checkpoint_audit.audit_checkpoint()` and `audit_batch()` for bounded read-only inspection of saved agent states. Checks plan authorization, cursor/evidence order, local digests, write attempts, approval status, and trace field allowlists.
- CP3: six local adversarial probes and 49 checkpoint audit tests. **The audit does not modify SQLite, authorize a resume, or replay actions.**

## Evidence image labeling

The six upgrade images under `screenshots/09_upgrade_*.png`–`screenshots/14_upgrade_*.png` are **rendered summaries of the verified checkpoint evidence**, not raw PowerShell screenshots or hosted CI screenshots. Previously captured original screenshots (01–08) remain separate. Do not represent these summaries as independent test execution or real production activity.

## Explicit limitations

- Local SHA-256 hashes are not signatures or proof against an attacker who can rewrite the data and manifests.
- Synthetic adversarial cases are development coverage, not a held-out security benchmark or generalized prompt-injection guarantee.
- Local `.env` was **not inspected** and is ignored by Git. Manually confirm that any previously exposed token was revoked/rotated; inspect history, screenshots, and licenses before publication.
- `.github/workflows/ci.yml` exercises Python 3.12 on Ubuntu and Windows and reruns the existing validator plus six CP3 probes after publication. Hosted Windows symlink privileges can differ from elevated local PowerShell. Do not claim that CI passed until both real jobs have completed successfully.
- Do not stage `CP1_Baseline/`, `CP2_Upgrade/`, `CP3_Recovery/`, `CP4_Release/`, `.venv/`, `.env`, `logs/`, `outputs/`, or generated database files.

## Final publication gates

1. Review release documentation, the six rendered summaries and original screenshots for personal data and secrets.
2. Confirm credential revocation (where applicable) and permitted licenses.
3. Run `Project14_CP4_Apply_And_Audit.ps1 -RepoRoot ... -Stage`, requiring exact allowlisted staged files and staged Git-index audit with zero findings.
4. Review `git diff --cached --stat`, `git diff --cached --check`, `git diff --cached --name-only` before any commit.
5. Commit and push only after explicit approval. Then verify **both** GitHub Actions OS jobs; record the actual commit SHA and run URL. No force push.
