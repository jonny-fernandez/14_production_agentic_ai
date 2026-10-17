"""Offline read-only CP4 package, evidence, redaction and credential safety audit.

Writes only outputs/cp4_prepublication_audit.json. Never opens local .env.
Not a credential revocation or production security certification.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys
from typing import Any

ALLOWED_TRACE_KEYS = frozenset({"trace_id", "scenario_id", "elapsed_ms", "evidence_count", "node", "status_after", "status_before", "step_index", "tool_call_count"})
TEXT_EXTENSIONS = frozenset({".py", ".md", ".txt", ".json", ".toml", ".yml", ".yaml", ".ini", ".cfg", ".ps1"})
IGNORED_DIRS = frozenset({".venv", "venv", ".git", ".pytest_cache", "__pycache__", "outputs", "logs", "artifacts", ".mypy_cache", ".ruff_cache"})
# Patterns are built in parts to avoid creating a false-positive credential in source code.
SUSPICIOUS = [
    re.compile("sk" + r"-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}"),
    re.compile("ghp" + r"_[A-Za-z0-9]{30,}"),
    re.compile("github_pat" + r"_[A-Za-z0-9_]{25,}"),
    re.compile("AK" + r"IA[0-9A-Z]{16}"),
    re.compile("-----BEGIN " + "PRIVATE KEY-----"),
]


def review_report(report: dict[str, Any], traces: list[dict[str, Any]], fixture_bytes: bytes, expected_hash: str, *, require_langgraph: bool = True) -> list[str]:
    """Recompute totals and assert exported traces match the report's source events."""
    problems: list[str] = []
    if hashlib.sha256(fixture_bytes).hexdigest() != expected_hash or report.get("fixture_sha256") != expected_hash:
        problems.append("Frozen fixture SHA256 mismatch")
    records = report.get("records", [])
    if len(records) != 23 or len({x.get("scenario_id") for x in records}) != 23:
        problems.append("Expected 23 unique scenarios")
    if any(x.get("passed") != (x.get("expected") == x.get("observed")) for x in records):
        problems.append("Scenario pass status inconsistent with expected/observed")
    metrics = report.get("metrics", {})
    if metrics.get("passed") != sum(x.get("passed") is True for x in records) or metrics.get("total") != len(records):
        problems.append("Aggregate scenario total mismatch")
    if any(x.get("passed") is not True for x in records):
        problems.append("One or more frozen scenarios failed")
    by_cat = {category: [x for x in records if x.get("category") == category] for category in ("positive", "safety", "recovery")}
    for cat, expected in (("positive", 5), ("safety", 14), ("recovery", 4)):
        sub = by_cat[cat]
        if len(sub) != expected or metrics.get("by_category", {}).get(cat) != {"passed": sum(x.get("passed") is True for x in sub), "total": len(sub)}:
            problems.append(f"Category metrics mismatch: {cat}")
    attempts = sum(x.get("tool_attempt_count", 0) for x in records)
    failures = sum(x.get("failed_tool_attempts", x.get("retried_tools", 0)) for x in records)
    if metrics.get("tool_attempts") != attempts or metrics.get("tool_attempt_failures") != failures:
        problems.append("Tool attempt count mismatch")
    times = [x.get("elapsed_ms") for x in records]
    if all(isinstance(v, (int, float)) and v >= 0 for v in times) and times:
        if abs(statistics.mean(times) - metrics.get("workflow_latency_mean_ms", -1)) > .002:
            problems.append("Mean latency does not reconcile")
        if sorted(times)[math.ceil(len(times) * .95) - 1] != metrics.get("workflow_latency_p95_ms_nearest_rank"):
            problems.append("P95 latency does not reconcile")
    else:
        problems.append("Invalid latency values")
    by_id = {}
    for event in traces:
        if set(event) != ALLOWED_TRACE_KEYS:
            problems.append("Trace includes missing or unauthorized metadata fields")
        by_id.setdefault(event.get("scenario_id"), []).append(event)
    if len(traces) != sum(len(x.get("trace_events", [])) for x in records):
        problems.append("Trace event count mismatch")
    for record in records:
        sid = record.get("scenario_id")
        source_events = [{"trace_id": record.get("trace_id"), "scenario_id": sid, **item} for item in record.get("trace_events", [])]
        if source_events != by_id.get(sid, []):
            problems.append(f"Trace reconciliation failed for {sid}")
        if any(x.get("trace_id") != record.get("trace_id") for x in by_id.get(sid, [])):
            problems.append(f"Trace ID mismatch for {sid}")
    if report.get("provider_mode") != "deterministic_synthetic_no_llm" or (require_langgraph and report.get("execution_mode") != "local_langgraph"):
        problems.append("Unexpected evaluation execution mode")
    return sorted(set(problems))


def find_possible_secrets(root: Path) -> list[str]:
    findings=[]
    for p in root.rglob("*"):
        if not p.is_file() or p.is_symlink() or p.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if any(part in IGNORED_DIRS for part in p.relative_to(root).parts):
            continue
        if p.name == ".env":
            continue
        if p.stat().st_size > 2_000_000:
            findings.append(f"Unscanned large file: {p.relative_to(root)}")
            continue
        try:
            data=p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"Unscanned non-UTF8 text file: {p.relative_to(root)}")
            continue
        if any(pattern.search(data) for pattern in SUSPICIOUS):
            findings.append(f"Potential secret pattern: {p.relative_to(root)}")
        if p.is_symlink():
            findings.append(f"Symlink in source tree: {p.relative_to(root)}")
    return findings


def git_tracked(root: Path) -> tuple[bool, list[str]]:
    if not (root / ".git").exists():
        return False, []
    proc=subprocess.run(["git", "ls-files", "-z"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    if proc.returncode: return True, ["Unable to inspect Git tracked paths"]
    tracked=[x.decode("utf-8", errors="replace") for x in proc.stdout.split(b"\0") if x]
    return True, [name for name in tracked if name == ".env" or name.startswith((".venv/", "outputs/", "logs/")) or name.endswith((".pyc", ".sqlite", ".sqlite3"))]


def dependency_inventory() -> list[dict[str, str]]:
    names = ("pydantic", "pytest", "langgraph", "fastapi", "uvicorn", "httpx")
    result=[]
    for name in names:
        try:
            dist=metadata.distribution(name)
            license_info=dist.metadata.get("License-Expression") or dist.metadata.get("License") or "UNSPECIFIED_IN_METADATA"
            if len(license_info) > 100: license_info="LONG_LICENSE_TEXT_REQUIRES_MANUAL_REVIEW"
            result.append({"package": name, "version":dist.version, "license_metadata": license_info})
        except metadata.PackageNotFoundError:
            result.append({"package":name,"version":"NOT_INSTALLED","license_metadata":"UNAVAILABLE"})
    return result


def main() -> int:
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from agentic_ai.evals.cp3_eval import LOCKED_FIXTURE_SHA256
    report_path=root / "outputs" / "cp3_evaluation_report.json"
    trace_path=root / "outputs" / "cp3_redacted_traces.jsonl"
    fixture=root / "data" / "evaluation" / "cp3_scenarios.json"
    blockers=[]
    warnings=[]
    if not report_path.is_file() or not trace_path.is_file():
        blockers.append("Missing CP3 report or trace output; run scripts/validate_cp3.py")
    else:
        report=json.loads(report_path.read_text(encoding="utf-8"))
        traces=[json.loads(x) for x in trace_path.read_text(encoding="utf-8").splitlines() if x.strip()]
        blockers.extend(review_report(report, traces, fixture.read_bytes(), LOCKED_FIXTURE_SHA256))
    blockers.extend(find_possible_secrets(root))
    git_exists, tracked_bad = git_tracked(root)
    if tracked_bad: blockers.append("Unsafe Git-tracked paths or Git inspection error: " + ", ".join(tracked_bad))
    if not git_exists: warnings.append("Git not initialized locally; staged-file audit must be repeated after initialization")
    ignored=(root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").exists() else ""
    if ".env" not in ignored.splitlines(): blockers.append(".gitignore does not contain exact .env exclusion")
    if (root / ".env").exists():
        warnings.append("Local .env exists: content deliberately not opened; verify key revocation/rotation manually before publishing")
    if not (root / "LICENSE").exists():
        warnings.append("No LICENSE file selected; decide distribution license before publication")
    if not (root / ".github" / "workflows" / "ci.yml").is_file():
        blockers.append("Local CI workflow candidate missing")
    deps=dependency_inventory()
    if any(d["version"] == "NOT_INSTALLED" for d in deps):
        warnings.append("Dependency inventory incomplete: check Python environment")
    warnings.append("Credential revocation, copyright/licenses, GitHub Actions and screenshot evidence need manual verification")
    out={"audit_version":"cp4-prepublication-v1","checkpoint":"CP4_PENDING","local_only":True,
         "blocked":bool(blockers), "blockers":sorted(set(blockers)), "warnings":warnings,
         "report_reconciled":not any("report" in x.lower() or "trace" in x.lower() or "scenario" in x.lower() or "fixture" in x.lower() or "latency" in x.lower() or "attempt" in x.lower() for x in blockers),
         "dependency_inventory":deps,"git_initialized":git_exists,
         "scope":"Pre-publication static and synthetic audit; not proof of CI/deployment/key rotation/license clearance"}
    output=root / "outputs" / "cp4_prepublication_audit.json"
    output.parent.mkdir(exist_ok=True, parents=True)
    output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("CP4 read-only prepublication audit (writes report only to ignored outputs/)")
    print("Audit status:", "BLOCKED" if blockers else "PASS WITH MANUAL REVIEW PENDING")
    print("Report/trace reconciliation:", "PASS" if out["report_reconciled"] else "CHECK REQUIRED")
    print("Suspect secrets/tracked-path issues:",len([b for b in blockers if "secret" in b.lower() or "tracked" in b.lower()]))
    for issue in sorted(set(blockers)): print("BLOCKER:",issue)
    for issue in warnings: print("REVIEW:",issue)
    print("Dependency inventory included in:",output)
    return 2 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
