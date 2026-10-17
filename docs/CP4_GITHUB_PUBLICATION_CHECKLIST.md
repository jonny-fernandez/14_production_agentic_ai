# Project 14 — Pre-publication checklist (CP4)

**State when created:** local CP4 suite completed and screenshot evidence captured; **nothing pushed to GitHub yet**. This file is a review aid, not evidence of a successful publication.

## Before staging

- [x] Eight original numbered screenshots under `screenshots/` on the user’s machine (observed screenshot count = 8).
- [x] MIT license selected by the project owner.
- [x] Owner reports revoking/rotating previously exposed API credentials; independently verifying revocation is outside local audit scope.
- [x] `git check-ignore -v .env` and `scripts/check_git_publication.py` passed before staging.
- [ ] Owner reviews the companion screenshot evidence Word document (kept outside the repo) and confirms it is saved/approved.
- [ ] Owner reviews the final README and confirms local-only and synthetic limitations.

## Staged content gate — before ANY `git commit` or `git push`

From Windows PowerShell inside the project root:

```powershell
git add -A
.\.venv\Scripts\python.exe scripts\check_git_publication.py
git diff --cached --check
git diff --cached --name-only | Select-String -Pattern '(^|/)(\.env($|\.)|\.venv/|venv/|outputs/|logs/|__pycache__/)|\.(sqlite|sqlite3|db|pyc|pem|p12|pfx|key)$'
git diff --cached --stat
```

Expected: security check PASS; `git diff --cached --check` produces no output; sensitive-path `Select-String` produces no output; review the staged summary. **If any check looks wrong, stop.** Do not treat an empty `Select-String` as proof that no secret exists; look through filenames and diffs before committing.

Inspect text changes and candidate set as needed:

```powershell
git diff --cached -- README.md .gitignore LICENSE .github/workflows/ci.yml
git status --short
```

## After review and user confirmation

- [ ] Commit changes locally only after staged-file review and screenshot handoff confirmation.
- [ ] Create/push a public GitHub repo only after the user explicitly proceeds.
- [ ] Visit GitHub Actions; verify both Windows and Ubuntu jobs on the **actual** commit (or debug and rerun).
- [ ] Capture genuine post-publication CI evidence separately; do not backfill synthetic success images.
- [ ] Report verified repo URL, commit SHA, workflow status, final scope/limits and only then add resume accomplishments.
