"""Tests for the CSV and Parquet loaders."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nz_privacy_auditor.loaders import load, load_csv, load_parquet


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    p = tmp_path / "data.csv"
    p.write_text("id,note\n1,IRD 49091850\n2,no pii\n", encoding="utf-8")
    return p


@pytest.fixture
def tsv_path(tmp_path: Path) -> Path:
    p = tmp_path / "data.tsv"
    p.write_text("id\tnote\n1\tIRD 49091850\n2\tno pii\n", encoding="utf-8")
    return p


@pytest.fixture
def parquet_path(tmp_path: Path) -> Path:
    p = tmp_path / "data.parquet"
    pd.DataFrame({"id": [1, 2], "note": ["IRD 49091850", "no pii"]}).to_parquet(p, engine="pyarrow")
    return p


class TestCSV:
    def test_load_csv_direct(self, csv_path: Path) -> None:
        df = load_csv(csv_path)
        assert list(df.columns) == ["id", "note"]
        assert len(df) == 2

    def test_load_csv_via_dispatcher(self, csv_path: Path) -> None:
        df = load(csv_path)
        assert len(df) == 2

    def test_load_tsv_via_dispatcher(self, tsv_path: Path) -> None:
        df = load(tsv_path)
        assert list(df.columns) == ["id", "note"]


class TestParquet:
    def test_load_parquet_direct(self, parquet_path: Path) -> None:
        df = load_parquet(parquet_path)
        assert len(df) == 2

    def test_load_parquet_via_dispatcher(self, parquet_path: Path) -> None:
        df = load(parquet_path)
        assert len(df) == 2


class TestDispatchErrors:
    def test_unknown_extension_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "data.xyz"
        p.write_text("nope")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            load(p)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load(tmp_path / "does-not-exist.csv")
