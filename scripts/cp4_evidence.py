"""Render screenshot-friendly factual summaries from local frozen CP3 report and traces."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

GROUPS={
    "approval": ("safe-report-preview", "safe-report-approval", "safe-report-rejection", "approval-replay"),
    "safety": ("unauthorized-write", "wrong-role", "unknown-tool", "unapproved-source", "injected-search", "injected-search-2", "untrusted-tool-text", "path-traversal"),
    "recovery": ("duplicate-request", "restart-resume", "transient-read", "persistent-read", "uncertain-write"),
    "traces": ("safe-analysis", "safe-report-approval"),
}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("section", choices=["approval", "safety", "recovery", "traces", "all"])
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    report=json.loads((root / "outputs" / "cp3_evaluation_report.json").read_text(encoding="utf-8"))
    if any(x.get("passed") is not True for x in report["records"]):
        raise SystemExit("BLOCKED: evaluation contains a failing scenario")
    by_id={r["scenario_id"]:r for r in report["records"]}
    groups=list(GROUPS) if args.section == "all" else [args.section]
    print("PROJECT 14 - VERIFIED LOCAL SYNTHETIC EVIDENCE")
    print("Fixture SHA256:",report["fixture_sha256"])
    print("Execution mode:",report["execution_mode"],"| Provider:",report["provider_mode"])
    for group in groups:
        print("\n==",group.upper(),"==")
        for key in GROUPS[group]:
            r=by_id[key]
            print(f"{key:24s} expected={r['expected']:18s} observed={r['observed']:18s} PASS={r['passed']} tool_attempts={r['tool_attempt_count']} failed_attempts={r.get('failed_tool_attempts',r.get('retried_tools',0))} evidence={r['evidence_count']}")
            if group == "traces":
                print("   trace_id=",r["trace_id"],"redacted_nodes:"," -> ".join(x["node"] for x in r["trace_events"]))
    print("\nScope: actual local synthetic scenario outcomes; not live accounts or production security evidence.")

if __name__ == "__main__":
    main()
