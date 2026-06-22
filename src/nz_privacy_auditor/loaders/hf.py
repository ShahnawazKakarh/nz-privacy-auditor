"""HuggingFace ``datasets`` loader (optional dependency).

This module imports the :mod:`datasets` package lazily; the package is only
available when the ``[hf]`` extra is installed.
"""

from __future__ import annotations

import pandas as pd


def load_hf(
    name: str,
    split: str = "train",
    config: str | None = None,
    streaming: bool = False,
    max_rows: int | None = None,
) -> pd.DataFrame:
    """Load a HuggingFace dataset split into a DataFrame.

    Args:
        name: Dataset name on the HuggingFace Hub (e.g. ``"glue"``,
            ``"username/my_dataset"``) or a local path.
        split: Split name (default ``"train"``).
        config: Optional dataset configuration name.
        streaming: If True, stream rows lazily instead of materialising.
        max_rows: If given, truncate to the first N rows (useful with
            ``streaming=True`` for large datasets).

    Returns:
        A pandas DataFrame containing the (possibly truncated) split.

    Raises:
        ImportError: when the optional ``datasets`` package is not installed.
    """
    try:
        from datasets import load_dataset
    except ImportError as exc:  # pragma: no cover - import-time check
        raise ImportError(
            "The 'datasets' package is required for HuggingFace loading. "
            "Install with: pip install 'nz-privacy-auditor[hf]'"
        ) from exc

    ds = load_dataset(name, config, split=split, streaming=streaming)

    if streaming:
        rows = []
        for i, row in enumerate(ds):
            if max_rows is not None and i >= max_rows:
                break
            rows.append(row)
        return pd.DataFrame(rows)

    if max_rows is not None:
        ds = ds.select(range(min(max_rows, len(ds))))
    return ds.to_pandas()
