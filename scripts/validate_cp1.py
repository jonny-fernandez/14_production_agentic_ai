"""Single validation command: read-only checks + deterministic tests, no network/API."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    print("CP1 deterministic validation | Python", sys.version.split()[0], flush=True)
    if sys.version_info < (3, 11):
        print("FAIL: Python >=3.11 required", flush=True)
        return 2
    if (root / ".env").exists():
        print("SECURITY WARNING: local .env exists; exclude it from archives/commits and rotate any exposed credentials.", flush=True)
    print("Fixture version: synthetic-v1; no paid API/network integrations executed.", flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    outcome = subprocess.run([sys.executable, "-m", "pytest", "-v", "tests"],
                             cwd=root, env=env, check=False)
    if outcome.returncode:
        print("CP1 tests FAILED; do not close checkpoint.", flush=True)
        return outcome.returncode
    from_path = str(root / "src")
    sys.path.insert(0, from_path)
    from agentic_ai.baseline import run_baseline
    outputs = [
        run_baseline("metrics", {"values": [10, 20, 30]}).model_dump(mode="json"),
        run_baseline("retrieval", {"query": "leave policy"}).model_dump(mode="json"),
        run_baseline("retrieval", {"query": "zxqrv nonexistent"}).model_dump(mode="json"),
        run_baseline("metrics", {"values": [1]}, role="guest").model_dump(mode="json"),
    ]
    print("--- Verified local CP1 smoke scenarios ---", flush=True)
    for output in outputs:
        print(json.dumps({key: output[key] for key in ("task_type", "status", "selected_tool", "evidence_sha256", "source_ids")},
                         sort_keys=True), flush=True)
    print("CP1 local checks completed; share full output for checkpoint review.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
