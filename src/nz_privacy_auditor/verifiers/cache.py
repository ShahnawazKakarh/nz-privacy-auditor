"""SQLite-backed cache for LLM verification results.

Re-running the auditor on the same dataset must not re-burn quota. The cache
key is a hash of (detector, value, context) so identical values in identical
context windows return immediately without an API call.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

from .base import Verdict, VerificationResult


def _make_key(detector: str, value: str, context: str) -> str:
    payload = json.dumps([detector, value, context], ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


class VerificationCache:
    """A tiny SQLite-backed cache for :class:`VerificationResult` entries."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS verifications (
                key         TEXT PRIMARY KEY,
                verdict     TEXT NOT NULL,
                confidence  REAL NOT NULL,
                reason      TEXT NOT NULL,
                created_at  REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    def get(self, detector: str, value: str, context: str) -> VerificationResult | None:
        key = _make_key(detector, value, context)
        row = self._conn.execute(
            "SELECT verdict, confidence, reason FROM verifications WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        verdict, confidence, reason = row
        return VerificationResult(
            verdict=Verdict(verdict),
            confidence=float(confidence),
            reason=reason,
            cached=True,
        )

    def put(
        self,
        detector: str,
        value: str,
        context: str,
        result: VerificationResult,
    ) -> None:
        key = _make_key(detector, value, context)
        self._conn.execute(
            "INSERT OR REPLACE INTO verifications "
            "(key, verdict, confidence, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                key,
                result.verdict.value,
                result.confidence,
                result.reason,
                time.time(),
            ),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> VerificationCache:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
