"""CP4 integrity, exported-trace and metric-semantics regressions."""
from pathlib import Path
import json
from agentic_ai.evals.cp3_eval import run_evaluation
from scripts.cp4_audit import ALLOWED_TRACE_KEYS, find_possible_secrets, review_report

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "evaluation" / "cp3_scenarios.json"

def _report_and_lines(tmp_path):
    from agentic_ai.evals.cp3_eval import LOCKED_FIXTURE_SHA256, write_report
    report = run_evaluation(FIXTURE, use_langgraph=False)
    report_path, trace_path = write_report(report, tmp_path)
    return report, [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()], LOCKED_FIXTURE_SHA256

def test_cp4_reconcile_report_and_export(tmp_path):
    report, rows, digest = _report_and_lines(tmp_path)
    assert review_report(report, rows, FIXTURE.read_bytes(), digest, require_langgraph=False) == []
    assert rows and all(set(item) == ALLOWED_TRACE_KEYS for item in rows)

def test_cp4_rejects_additional_trace_fields(tmp_path):
    report, rows, digest = _report_and_lines(tmp_path)
    rows[0]["private_query"] = "untrusted info"
    assert any("unauthorized" in issue or "Trace" in issue for issue in review_report(report, rows, FIXTURE.read_bytes(), digest, require_langgraph=False))

def test_cp4_rejects_tampered_expected_outcomes(tmp_path):
    report, rows, digest = _report_and_lines(tmp_path)
    report["records"][0]["observed"] = "failed"
    assert review_report(report, rows, FIXTURE.read_bytes(), digest, require_langgraph=False)

def test_cp4_failed_attempts_are_not_synonymous_with_retries(tmp_path):
    report, rows, digest = _report_and_lines(tmp_path)
    by_id = {item["scenario_id"]: item for item in report["records"]}
    assert by_id["uncertain-write"]["failed_tool_attempts"] == 1
    assert by_id["uncertain-write"]["tool_attempt_count"] == 3
    assert "retried_tools" not in by_id["uncertain-write"]
    assert report["metrics"]["tool_attempt_failures"] == 4

def test_cp4_secret_scan_excludes_local_env_but_flags_key_like_text(tmp_path):
    (tmp_path / ".env").write_text("DO_NOT_OPEN_DURING_AUDIT",encoding="utf-8")
    assert not find_possible_secrets(tmp_path)
    (tmp_path / "unsafe.py").write_text("x = 'sk-" + "A" * 30 + "'", encoding="utf-8")
    assert find_possible_secrets(tmp_path)
