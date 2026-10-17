"""Restricted local report sink: synthetic, immutable, no arbitrary file paths."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from agentic_ai.contracts import ReportInput


def make_report_tool(project_root: Path):
    root = project_root.resolve()
    reports = root / "outputs" / "reports"

    def save_report(report_id: str, metrics: dict, source_ids: list[str], evidence_sha256: list[str]) -> dict:
        request = ReportInput.model_validate({"report_id": report_id, "metrics": metrics,
                                               "source_ids": source_ids, "evidence_sha256": evidence_sha256})
        # Refuse attacker-controlled directory symlinks rather than following them.
        if (root / "outputs").is_symlink() or reports.is_symlink():
            raise ValueError("Refusing symlink output directory")
        report_dir = reports.resolve()
        if root not in report_dir.parents:
            raise ValueError("Report destination is outside project root")
        path = report_dir / (request.report_id + ".json")
        payload = {"fixture_version": "synthetic-v1", "report_id": request.report_id,
                   "metrics": request.metrics.model_dump(), "source_ids": request.source_ids,
                   "evidence_sha256": request.evidence_sha256}
        content = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        report_dir.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise ValueError("Refusing symlink report target")
        existed = False
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(content)
        except FileExistsError:
            existed = True
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise ValueError("Existing immutable report conflicts with requested content")
        if path.read_text(encoding="utf-8") != content:
            raise OSError("Report could not be verified after writing")
        return {"path": "outputs/reports/" + request.report_id + ".json",
                "sha256": digest, "already_existed": existed}

    return save_report
