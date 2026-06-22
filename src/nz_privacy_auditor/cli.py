"""Command-line interface for nz-privacy-auditor.

Usage::

    nz-privacy-auditor scan path/to/data.csv
    nz-privacy-auditor scan path/to/data.parquet --format json --output report.json
    nz-privacy-auditor scan data.csv --detector ird,nhi --min-confidence 0.7
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__
from .loaders import load
from .report import render_console, to_json
from .scanner import Scanner, default_detectors

# Map of CLI detector keys to detector classes.
_DETECTOR_KEYS = {d.name: d.__class__ for d in default_detectors()}


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="nz-privacy-auditor")
def main() -> None:
    """Privacy Act 2020 compliance auditor for ML datasets."""


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["console", "json"]),
    default="console",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Write output to a file instead of stdout (JSON format only).",
)
@click.option(
    "--detector",
    "detectors_csv",
    default=None,
    help=(
        "Comma-separated detector names to enable. "
        f"Choices: {', '.join(sorted(_DETECTOR_KEYS))}. Default: all."
    ),
)
@click.option(
    "--min-confidence",
    type=click.FloatRange(0.0, 1.0),
    default=0.0,
    show_default=True,
    help="Drop findings below this confidence threshold.",
)
@click.option(
    "--fail-on-finding",
    is_flag=True,
    default=False,
    help="Exit with status 1 if any findings are emitted (useful in CI).",
)
def scan(
    path: Path,
    output_format: str,
    output: Path | None,
    detectors_csv: str | None,
    min_confidence: float,
    fail_on_finding: bool,
) -> None:
    """Scan a dataset for Privacy Act 2020 PII issues."""
    # Resolve detector set
    if detectors_csv:
        keys = [k.strip() for k in detectors_csv.split(",") if k.strip()]
        unknown = [k for k in keys if k not in _DETECTOR_KEYS]
        if unknown:
            raise click.BadParameter(
                f"Unknown detector(s): {', '.join(unknown)}. "
                f"Valid: {', '.join(sorted(_DETECTOR_KEYS))}",
                param_hint="--detector",
            )
        detectors = [_DETECTOR_KEYS[k]() for k in keys]
    else:
        detectors = default_detectors()

    df = load(path)
    scanner = Scanner(detectors=detectors, min_confidence=min_confidence)
    result = scanner.scan_dataframe(df)

    if output_format == "json":
        payload = to_json(result)
        if output:
            output.write_text(payload, encoding="utf-8")
            click.echo(f"Wrote report to {output}")
        else:
            click.echo(payload)
    else:
        if output:
            raise click.BadParameter(
                "--output is only supported with --format json",
                param_hint="--output",
            )
        render_console(result)

    if fail_on_finding and result.total_findings > 0:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
