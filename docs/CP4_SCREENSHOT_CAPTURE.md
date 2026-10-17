# CP4 real screenshot capture plan (before first GitHub publication)

This file is a **plan**, not a claim that images already exist. Capture **genuine** PowerShell/VS Code output on your own system after running commands. Do not generate mock console images.

Folder: `screenshots/` (create it locally after evidence is reviewed). Use these exact filenames:

| Filename | What must actually be visible | Command |
| --- | --- | --- |
| `01_cp4_full_validation.png` | Full local test result and CP4 final validation status, no fabricated CI | `python scripts/validate_cp4.py` via `.venv` |
| `02_cp3_frozen_evaluation.png` | Real 23/23 report, fixture SHA, latency and 0 paid requests | `python scripts/validate_cp3.py` |
| `03_approval_and_rejection.png` | Preview, success after synthetic approval, rejected approval and replay protection | `python scripts/cp4_evidence.py approval` |
| `04_unsafe_action_denials.png` | Actual role, unauthorized tools, traversal, unapproved sources and injection scenario results | `python scripts/cp4_evidence.py safety` |
| `05_retry_resume_and_uncertain_write.png` | Duplicate handling, resume, successful retry, exhausted retry, uncertain write not retried | `python scripts/cp4_evidence.py recovery` |
| `06_evidence_trace_ids.png` | Real redacted trace IDs/nodes from recorded synthetic analysis/report | `python scripts/cp4_evidence.py traces` |
| `07_cp4_security_dependency_audit.png` | Local credential exclusion/trace reconciliation and dependency inventory warning statuses | `python scripts/cp4_audit.py` |
| `08_prepublication_git_review.png` | Actual `git status --short` and `git check-ignore .env` output if Git is initialized; don't stage secrets | manual Git commands, **only after file review** |

Use the full interpreter form for commands: `.\.venv\Scripts\python.exe` instead of `python`.

**Sequence:** Technical validation -> upload audit JSON & actual PNGs -> assistant builds Word doc **embedding** actual PNGs and filenames -> user confirms files are saved -> finish README/license/security review -> create/push repository -> verify real GitHub Actions. `09_github_actions_success.png` can only be captured after a real successful GitHub Actions run; add it as a post-publication supplement, never pretend it exists in the pre-publication Word document.

The repository does **not** yet have verified GitHub Actions outcomes. Synthetic tests are not live integrations, cloud deployment, or security certification. Never include `.env`, raw state SQLite, user records or secrets in screenshots.
