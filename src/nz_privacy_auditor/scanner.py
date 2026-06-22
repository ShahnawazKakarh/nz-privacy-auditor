"""Dataset-level scanner that orchestrates the detector pipeline.

The :class:`Scanner` walks every string-typed column of a DataFrame and
applies each configured :class:`Detector` to each cell. Results are
collected into a :class:`ScanResult` with per-cell findings and aggregate
summary statistics.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .detectors import (
    AddressDetector,
    Detector,
    DriverLicenceDetector,
    Finding,
    IRDDetector,
    MaoriNameDetector,
    NHIDetector,
    PhoneDetector,
    Severity,
)

if TYPE_CHECKING:
    import pandas as pd


def default_detectors() -> list[Detector]:
    """Return the default detector set (all six built-in detectors)."""
    return [
        IRDDetector(),
        NHIDetector(),
        DriverLicenceDetector(),
        PhoneDetector(),
        AddressDetector(),
        MaoriNameDetector(),
    ]


@dataclass(frozen=True)
class CellFinding:
    """A :class:`Finding` enriched with its row index, column name, and the
    full cell value (kept so an LLM verification pass can use surrounding
    context).
    """

    row: int
    column: str
    finding: Finding
    cell_value: str = ""


@dataclass
class ScanResult:
    """Aggregate result of scanning a DataFrame."""

    rows_scanned: int
    columns_scanned: list[str]
    detectors_used: list[str]
    findings: list[CellFinding] = field(default_factory=list)

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    def count_by_detector(self) -> dict[str, int]:
        return dict(Counter(cf.finding.detector for cf in self.findings))

    def count_by_severity(self) -> dict[str, int]:
        return dict(Counter(cf.finding.severity.value for cf in self.findings))

    def count_by_column(self) -> dict[str, int]:
        return dict(Counter(cf.column for cf in self.findings))


class Scanner:
    """Orchestrates detection across a DataFrame.

    Args:
        detectors: detector instances to run. Defaults to the six built-in
            detectors via :func:`default_detectors`.
        min_confidence: drop findings with confidence below this threshold
            after detection. Defaults to 0.0 (no filtering).
    """

    def __init__(
        self,
        detectors: list[Detector] | None = None,
        min_confidence: float = 0.0,
    ) -> None:
        self.detectors = detectors if detectors is not None else default_detectors()
        self.min_confidence = min_confidence

    def scan_dataframe(self, df: pd.DataFrame) -> ScanResult:
        """Scan every string-typed column of ``df`` and return a ScanResult."""
        import pandas as pd

        # Accept legacy object dtype and pandas StringDtype.
        string_cols = [
            c for c in df.columns if df[c].dtype == object or pd.api.types.is_string_dtype(df[c])
        ]
        result = ScanResult(
            rows_scanned=len(df),
            columns_scanned=string_cols,
            detectors_used=[d.name for d in self.detectors],
        )

        for col in string_cols:
            series = df[col]
            for row_idx, value in enumerate(series):
                if value is None:
                    continue
                if not isinstance(value, str):
                    continue
                if not value:
                    continue
                for detector in self.detectors:
                    for finding in detector.scan(value):
                        if finding.confidence < self.min_confidence:
                            continue
                        result.findings.append(
                            CellFinding(
                                row=row_idx,
                                column=col,
                                finding=finding,
                                cell_value=value,
                            )
                        )
        return result

    def scan_value(self, value: str) -> list[Finding]:
        """Scan a single string with all configured detectors."""
        out: list[Finding] = []
        for detector in self.detectors:
            for finding in detector.scan(value):
                if finding.confidence < self.min_confidence:
                    continue
                out.append(finding)
        return out


__all__ = [
    "CellFinding",
    "ScanResult",
    "Scanner",
    "Severity",
    "default_detectors",
]
