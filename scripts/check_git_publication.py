"""Read-only prepublication file-selection audit. Never opens local .env files.

Checks files visible to `git add .` AND already staged files for prohibited
secret paths; detects common credential patterns in text files. Does not stage,
commit, push, rotate keys, or verify license provenance.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

TEXT_EXTS = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".ps1", ".example"}
SUSPICIOUS = (
    re.compile("sk" + r"-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}"),
    re.compile("ghp" + r"_[A-Za-z0-9]{30,}"),
    re.compile("github_pat" + r"_[A-Za-z0-9_]{25,}"),
    re.compile("AK" + r"IA[0-9A-Z]{16}"),
    re.compile("-----BEGIN " + "PRIVATE KEY-----"),
)


def git_bytes(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError("Git command failed: " + " ".join(args) + " (code " + str(result.returncode) + ")")
    return result.stdout


def reject_path(name: str) -> bool:
    parts = PurePosixPath(name.replace("\\", "/")).parts
    for part in parts:
        lower = part.lower()
        if lower == ".env.example":
            continue
        if (lower == ".env" or lower.startswith(".env.") or lower.endswith(".env")
                or lower in {".venv", "venv", "__pycache__", ".git", "secrets"}
                or lower.endswith((".pem", ".p12", ".pfx", ".key", ".sqlite", ".sqlite3", ".db", ".pyc"))
                or lower == "credentials.json"):
            return True
    return False


def scan_text(data: bytes, name: str, findings: list[str]) -> None:
    if len(data) > 2_000_000:
        findings.append(f"Unscanned oversized text: {name}")
        return
    try:
        value = data.decode("utf-8")
    except UnicodeDecodeError:
        findings.append(f"Unscanned non-UTF8 text: {name}")
        return
    if any(p.search(value) for p in SUSPICIOUS):
        findings.append(f"Potential credential pattern: {name}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if not (root / ".git").exists():
        print("BLOCK: Git not initialized in the Project 14 directory.")
        return 2
    findings: list[str] = []
    # Explicitly require actual environment files to be ignored. Never read them.
    ignored = (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").is_file() else ""
    for required in (".env", ".env.*", "!.env.example"):
        if required not in ignored.splitlines():
            findings.append(f"Missing .gitignore safeguard: {required}")
    candidates = git_bytes(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    names = sorted({s.decode("utf-8", errors="replace") for s in candidates.split(b"\0") if s})
    staged = git_bytes(root, "ls-files", "--cached", "-z")
    staged_names = {s.decode("utf-8", errors="replace") for s in staged.split(b"\0") if s}
    for name in names:
        if reject_path(name):
            findings.append(f"Prohibited Git file path: {name}")
            continue
        if name.startswith(("outputs/", "logs/", "data/raw/", "data/processed/")) and not name.endswith("/.gitkeep"):
            findings.append(f"Generated or raw-data path not approved for Git: {name}")
            continue
        if PurePosixPath(name).suffix.lower() not in TEXT_EXTS and PurePosixPath(name).name != ".env.example":
            continue
        if name in staged_names:
            try:
                content = git_bytes(root, "show", ":" + name)
            except RuntimeError:
                findings.append(f"Could not read staged content: {name}")
                continue
        else:
            target = root / name
            if target.is_symlink():
                findings.append(f"Review symlink before publication: {name}")
                continue
            if not target.is_file():
                continue
            content = target.read_bytes()
        scan_text(content, name, findings)
    print(f"Git publication preflight: {len(names)} candidate files, {len(staged_names)} indexed files")
    print("Policy: local .env and environment variants must never be staged; .env.example allowed.")
    if findings:
        for finding in sorted(set(findings)):
            print("BLOCK:", finding)
        return 2
    print("PASS: no prohibited Git file paths or common credential patterns detected in candidate text files.")
    print("LIMITATION: not a complete secret scan or proof of credential revocation; GitHub has not been published.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
