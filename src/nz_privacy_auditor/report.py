"""Report rendering for :class:`ScanResult` instances.

Supports JSON serialisation and a Rich console table view. HTML reports
are planned for a later release.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

    from .scanner import ScanResult


def to_dict(result: ScanResult) -> dict[str, Any]:
    """Convert a ScanResult into a JSON-serialisable dictionary."""
    return {
        "summary": {
            "rows_scanned": result.rows_scanned,
            "columns_scanned": result.columns_scanned,
            "detectors_used": result.detectors_used,
            "total_findings": result.total_findings,
            "by_detector": result.count_by_detector(),
            "by_severity": result.count_by_severity(),
            "by_column": result.count_by_column(),
        },
        "findings": [
            {
                "row": cf.row,
                "column": cf.column,
                "detector": cf.finding.detector,
                "severity": cf.finding.severity.value,
                "value": cf.finding.value,
                "start": cf.finding.start,
                "end": cf.finding.end,
                "confidence": cf.finding.confidence,
                "context": cf.finding.context,
            }
            for cf in result.findings
        ],
    }


def to_json(result: ScanResult, indent: int | None = 2) -> str:
    """Render the ScanResult as a JSON string."""
    return json.dumps(to_dict(result), indent=indent, ensure_ascii=False)


def render_console(result: ScanResult, console: Console | None = None) -> None:
    """Render a human-readable summary + findings table to the console."""
    from rich.console import Console
    from rich.table import Table

    console = console or Console()

    # Summary panel
    console.print(
        f"[bold]nz-privacy-auditor[/bold] scanned "
        f"[cyan]{result.rows_scanned}[/cyan] rows across "
        f"[cyan]{len(result.columns_scanned)}[/cyan] string columns"
    )
    console.print(
        f"Total findings: [bold]{result.total_findings}[/bold]"
        f"  \u2022  Detectors: {', '.join(result.detectors_used)}"
    )

    if not result.findings:
        console.print("[green]No PII findings.[/green]")
        return

    # Severity / detector breakdown
    sev = result.count_by_severity()
    det = result.count_by_detector()
    console.print(
        "By severity: " + ", ".join(f"[bold]{k}[/bold] {v}" for k, v in sorted(sev.items()))
    )
    console.print(
        "By detector: " + ", ".join(f"[bold]{k}[/bold] {v}" for k, v in sorted(det.items()))
    )

    # Findings table (truncate value to avoid wide output)
    table = Table(title="Findings", show_lines=False)
    table.add_column("row", justify="right")
    table.add_column("column")
    table.add_column("detector")
    table.add_column("severity")
    table.add_column("confidence", justify="right")
    table.add_column("value")

    for cf in result.findings[:200]:  # cap to first 200 for readability
        value = cf.finding.value
        if len(value) > 40:
            value = value[:37] + "..."
        table.add_row(
            str(cf.row),
            cf.column,
            cf.finding.detector,
            cf.finding.severity.value,
            f"{cf.finding.confidence:.2f}",
            value,
        )
    console.print(table)
    if result.total_findings > 200:
        console.print(f"[dim]\u2026 {result.total_findings - 200} more findings not shown.[/dim]")


__all__ = ["render_console", "to_dict", "to_json"]
