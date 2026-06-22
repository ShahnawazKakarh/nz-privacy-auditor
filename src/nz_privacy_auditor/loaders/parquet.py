"""Parquet loader (via pyarrow)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_parquet(path: str | Path) -> pd.DataFrame:
    """Load a Parquet file into a DataFrame using the pyarrow engine."""
    return pd.read_parquet(path, engine="pyarrow")
