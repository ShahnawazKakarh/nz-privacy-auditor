"""Dataset loaders.

Each loader returns a :class:`pandas.DataFrame` regardless of the source
format. The dispatch helper :func:`load` auto-detects the format from the
path extension.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .csv import load_csv
from .parquet import load_parquet

__all__ = ["load", "load_csv", "load_parquet"]


def load(path: str | Path) -> pd.DataFrame:
    """Load a dataset by path, dispatching on the extension.

    Supports ``.csv``, ``.tsv``, ``.parquet``, and ``.pq``. For HuggingFace
    datasets, use :func:`load_hf` from :mod:`nz_privacy_auditor.loaders.hf`
    directly (it depends on the optional ``datasets`` package).

    Raises:
        ValueError: when the extension is not recognised.
        FileNotFoundError: when the path does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    suffix = p.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return load_csv(p, sep="\t" if suffix == ".tsv" else ",")
    if suffix in {".parquet", ".pq"}:
        return load_parquet(p)
    raise ValueError(
        f"Unsupported file extension '{suffix}'. "
        "Supported: .csv, .tsv, .parquet, .pq. "
        "For HuggingFace datasets use nz_privacy_auditor.loaders.hf.load_hf()."
    )
