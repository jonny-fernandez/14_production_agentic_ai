"""Runs all project tests and the frozen CP3 LangGraph evaluation; nonzero on failure."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    print(f"CP3 evaluation | Python {sys.version.split()[0]}", flush=True)
    if (root / ".env").exists():
        print("SECURITY WARNING: local .env exists. Do not archive or commit; rotate exposed credentials.", flush=True)
    try:
        from langgraph.graph import StateGraph  # noqa: F401
        from fastapi import FastAPI  # noqa: F401
    except ImportError as exc:
        print(f"FAILED: missing CP2 runtime package {type(exc).__name__}", flush=True)
        return 2
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run([sys.executable, "-m", "pytest", "-v", "tests"], cwd=root, env=env, check=False)
    if completed.returncode:
        print("CP3 FAILED: tests did not pass; leave checkpoint open.", flush=True)
        return completed.returncode
    sys.path.insert(0, str(root / "src"))
    from agentic_ai.evals.cp3_eval import run_evaluation, write_report
    try:
        report = run_evaluation(root / "data" / "evaluation" / "cp3_scenarios.json", use_langgraph=True)
        report_path, trace_path = write_report(report, root / "outputs")
    except Exception as exc:
        print(f"CP3 FAILED: evaluation error: {type(exc).__name__}: {exc}", flush=True)
        return 3
    metrics = report["metrics"]
    print("--- CP3 frozen synthetic evaluation ---", flush=True)
    print(f"fixture SHA256: {report['fixture_sha256']}", flush=True)
    print(f"scenario results: {metrics['passed']}/{metrics['total']}", flush=True)
    for group, scores in metrics["by_category"].items():
        print(f"  {group}: {scores['passed']}/{scores['total']}", flush=True)
    print(f"mean workflow latency: {metrics['workflow_latency_mean_ms']} ms", flush=True)
    print(f"p95 workflow latency (nearest rank; n={metrics['workflow_latency_n']}): {metrics['workflow_latency_p95_ms_nearest_rank']} ms", flush=True)
    print(f"tool attempts: {metrics['tool_attempts']}; failed attempts: {metrics['tool_attempt_failures']}", flush=True)
    print("Mode: synthetic local LangGraph; 0 paid LLM calls; CPU/hosting cost excluded", flush=True)
    print(f"Report: {report_path}", flush=True)
    print(f"Redacted traces: {trace_path}", flush=True)
    if metrics["passed"] != metrics["total"]:
        for record in report["records"]:
            if not record["passed"]:
                print(f"FAIL {record['scenario_id']}: expected {record['expected']}, got {record['observed']}", flush=True)
        print("CP3 FAILED: evaluation scenarios not all passing.", flush=True)
        return 4
    print("CP3 local checks passed; share outputs for checkpoint review.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
