"""CSV / TSV loader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_csv(path: str | Path, sep: str = ",") -> pd.DataFrame:
    """Load a CSV or TSV file. Strings are loaded as ``str`` dtype.

    Numeric columns are preserved as numeric; only object-dtype columns are
    scanned for PII downstream.
    """
    return pd.read_csv(path, sep=sep)
