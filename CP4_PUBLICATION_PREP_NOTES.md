# Project 14 — MIT and Git safety preparation

- Project license: MIT, with 2026 Jonnathan Fernandez copyright.
- Keep local `.env` and its variants private. `.gitignore` ignores them, with an exception for the placeholder-only `.env.example`.
- All eight original PNG screenshots are provided under `screenshots/`.
- `scripts/check_git_publication.py` is a **read-only** preflight: it lists would-be Git files and staged files, refuses private paths, and checks common credential patterns in text. It does not read `.env`, stage files, commit, or push.
- The previously exposed key was reported revoked/rotated by the user; no independent verification is possible from local outputs.
- **Do not commit/push yet.** First confirm the screenshots are saved and the Word evidence document was reviewed. Then perform final README/staging review and verify GitHub CI after publishing.
- The existing project README remains unchanged in this preparation archive. It will be finalized after screenshot confirmation.
