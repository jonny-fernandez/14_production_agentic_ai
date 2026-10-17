"""Mandatory Windows gate; returns nonzero if LangGraph is unavailable or tests fail."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    print("CP2 validation | Python", sys.version.split()[0], flush=True)
    try:
        import langgraph.graph  # noqa: F401
        import fastapi  # noqa: F401
    except ImportError as exc:
        print("FAILED: missing CP2 dependency:", type(exc).__name__, flush=True)
        return 2
    if (root / ".env").exists():
        print("SECURITY WARNING: local .env exists; do not share/archive it; rotate exposed keys.", flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    result = subprocess.run([sys.executable, "-m", "pytest", "-v", "tests"],
                            cwd=root, env=env, check=False)
    if result.returncode:
        print("CP2 FAILED. Share tracebacks for repair; do not close checkpoint.", flush=True)
        return result.returncode
    sys.path.insert(0, str(root / "src"))
    from agentic_ai.workflow import WorkflowEngine
    print("--- Local graph smoke scenarios: no paid models or network ---", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        engine = WorkflowEngine(Path(tmp), use_langgraph=True)
        if engine.graph is None:
            print("FAILED: LangGraph compilation unavailable", flush=True)
            return 2
        arguments = {"metrics": {"values": [10, 20, 30]}, "retrieval": {"query": "leave policy"}}
        for req in (
            {"request_id": "cp2-analysis-01", "task_type": "analysis", **arguments},
            {"request_id": "cp2-reportdry-01", "task_type": "report", "report_id": "cp2-preview", **arguments},
            {"request_id": "cp2-reportauth-01", "task_type": "report", "report_id": "cp2-approved", "dry_run": False, **arguments},
        ):
            role = "manager" if req["task_type"] == "report" else "analyst"
            state = engine.start(req, role=role)
            print(f"{state.request_id}: {state.status}, step={state.step_index}, evidence={len(state.evidence)}", flush=True)
            if state.status not in {"success", "dry_run", "awaiting_approval"}:
                return 3
            if state.status == "awaiting_approval":
                state = engine.decide(state.request_id, reviewer="local-demo-reviewer",
                                      approved=True, reason="Approve synthetic local report test")
                print(f"{state.request_id} after approval: {state.status}, evidence={len(state.evidence)}", flush=True)
                if state.status != "success":
                    return 3
        engine.store.close()
    print("CP2 checks completed. Share this output; CP2 is not complete until reviewed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
