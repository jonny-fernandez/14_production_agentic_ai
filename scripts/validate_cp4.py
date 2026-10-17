"""Final local CP4 pre-publication checks: real pytest+LangGraph then static/evidence audit."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[1]
    print("CP4 Windows/Linux pre-publication validation | Python",sys.version.split()[0],flush=True)
    for file in ("validate_cp3.py","cp4_audit.py"):
        result=subprocess.run([sys.executable, str(root / "scripts" / file)], cwd=root,check=False)
        if result.returncode:
            print("CP4 BLOCKED by",file,"return code",result.returncode,flush=True)
            return result.returncode
    print("CP4 technical checks passed. Manual key rotation, screenshot Word review, GitHub publication and live CI verification still PENDING.",flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
