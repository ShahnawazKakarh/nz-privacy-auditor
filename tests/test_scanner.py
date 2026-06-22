"""Tests for the Scanner orchestration layer."""

from __future__ import annotations

import pandas as pd

from nz_privacy_auditor import Scanner
from nz_privacy_auditor.detectors import IRDDetector, NHIDetector


class TestScannerSingleValue:
    def test_scan_value_finds_ird_and_nhi(self) -> None:
        scanner = Scanner()
        findings = scanner.scan_value("IRD 49091850 and NHI ZAA0067 on file.")
        detectors_hit = {f.detector for f in findings}
        assert "ird" in detectors_hit
        assert "nhi" in detectors_hit

    def test_scan_value_respects_min_confidence(self) -> None:
        scanner = Scanner(min_confidence=0.95)
        # Bare driver-licence pattern with no keyword: confidence 0.5 -> dropped.
        findings = scanner.scan_value("Reference BQ739482 follows.")
        assert findings == []

    def test_custom_detector_subset(self) -> None:
        scanner = Scanner(detectors=[IRDDetector(), NHIDetector()])
        # Driver licence detector not in set -> no driver_licence findings.
        findings = scanner.scan_value("Driver licence BQ739482 IRD 49091850")
        assert {f.detector for f in findings} == {"ird"}


class TestScannerDataFrame:
    def test_scan_dataframe_basic(self) -> None:
        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "note": [
                    "Patient NHI ZAA0067 admitted.",
                    "No PII in this row.",
                    "IRD on file: 49091850.",
                ],
            }
        )
        result = Scanner().scan_dataframe(df)
        assert result.rows_scanned == 3
        assert result.columns_scanned == ["note"]
        assert result.total_findings == 2
        by_detector = result.count_by_detector()
        assert by_detector == {"nhi": 1, "ird": 1}

    def test_scan_dataframe_ignores_numeric_columns(self) -> None:
        df = pd.DataFrame({"score": [1, 2, 3], "value": [49091850, 0, 0]})
        result = Scanner().scan_dataframe(df)
        # Numeric IRD-shaped value is NOT scanned because the column is int.
        assert result.total_findings == 0

    def test_scan_dataframe_handles_nulls(self) -> None:
        df = pd.DataFrame({"note": ["IRD 49091850", None, "", "no pii"]})
        result = Scanner().scan_dataframe(df)
        assert result.total_findings == 1

    def test_summary_counts(self) -> None:
        df = pd.DataFrame(
            {
                "a": ["NHI ZAA0067", "IRD 49091850"],
                "b": ["Auckland phone +64 21 123 4567", "no pii"],
            }
        )
        result = Scanner().scan_dataframe(df)
        assert result.total_findings >= 3
        sev = result.count_by_severity()
        assert "high" in sev  # IRD + NHI
        assert "medium" in sev  # phone
        # b column has the phone; a column has IRD + NHI
        by_col = result.count_by_column()
        assert by_col["a"] >= 2
        assert by_col["b"] >= 1
