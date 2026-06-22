"""Tests for the CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from nz_privacy_auditor.cli import main


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    p = tmp_path / "data.csv"
    p.write_text(
        "id,note\n1,IRD 49091850 on file\n2,no pii here\n3,NHI ZAA0067 admitted\n",
        encoding="utf-8",
    )
    return p


class TestVersion:
    def test_version_flag(self) -> None:
        result = CliRunner().invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "nz-privacy-auditor" in result.output


class TestScan:
    def test_scan_console(self, csv_path: Path) -> None:
        result = CliRunner().invoke(main, ["scan", str(csv_path)])
        assert result.exit_code == 0
        assert "ird" in result.output
        assert "nhi" in result.output

    def test_scan_json_stdout(self, csv_path: Path) -> None:
        result = CliRunner().invoke(main, ["scan", str(csv_path), "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["summary"]["total_findings"] == 2
        detectors = {f["detector"] for f in payload["findings"]}
        assert detectors == {"ird", "nhi"}

    def test_scan_json_file(self, csv_path: Path, tmp_path: Path) -> None:
        out = tmp_path / "report.json"
        result = CliRunner().invoke(
            main,
            ["scan", str(csv_path), "--format", "json", "--output", str(out)],
        )
        assert result.exit_code == 0
        assert out.exists()
        payload = json.loads(out.read_text())
        assert payload["summary"]["total_findings"] == 2

    def test_scan_detector_filter(self, csv_path: Path) -> None:
        result = CliRunner().invoke(
            main,
            ["scan", str(csv_path), "--detector", "ird", "--format", "json"],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        detectors = {f["detector"] for f in payload["findings"]}
        assert detectors == {"ird"}

    def test_scan_unknown_detector_errors(self, csv_path: Path) -> None:
        result = CliRunner().invoke(main, ["scan", str(csv_path), "--detector", "bogus"])
        assert result.exit_code != 0
        assert "Unknown detector" in result.output

    def test_min_confidence_filter(self, csv_path: Path) -> None:
        # All built-in findings here are checksum-validated -> confidence 1.0.
        # Setting threshold to 1.0 should keep them, 1.01 should drop them.
        result = CliRunner().invoke(
            main, ["scan", str(csv_path), "--min-confidence", "1.0", "--format", "json"]
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["summary"]["total_findings"] == 2

    def test_fail_on_finding_flag(self, csv_path: Path) -> None:
        result = CliRunner().invoke(main, ["scan", str(csv_path), "--fail-on-finding"])
        assert result.exit_code == 1

    def test_fail_on_finding_clean(self, tmp_path: Path) -> None:
        clean = tmp_path / "clean.csv"
        clean.write_text("id,note\n1,no pii\n2,still none\n", encoding="utf-8")
        result = CliRunner().invoke(main, ["scan", str(clean), "--fail-on-finding"])
        assert result.exit_code == 0
