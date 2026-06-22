"""Tests for the LLM verification layer.

The Gemini client is mocked end-to-end \u2014 no real API calls are made. We
test the cache, the verifier's response parsing and error handling, and
the ``apply_verification`` re-scoring logic.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from nz_privacy_auditor import Scanner, apply_verification
from nz_privacy_auditor.verifiers import (
    GeminiVerifier,
    QuotaExceededError,
    Verdict,
    VerificationCache,
    VerificationResult,
)

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class TestCache:
    def test_put_and_get_roundtrip(self, tmp_path: Path) -> None:
        cache = VerificationCache(tmp_path / "c.sqlite")
        result = VerificationResult(verdict=Verdict.CONFIRMED, confidence=0.9, reason="ok")
        cache.put("driver_licence", "BQ739482", "Reference BQ739482", result)

        got = cache.get("driver_licence", "BQ739482", "Reference BQ739482")
        assert got is not None
        assert got.verdict is Verdict.CONFIRMED
        assert got.confidence == pytest.approx(0.9)
        assert got.reason == "ok"
        assert got.cached is True

    def test_miss_returns_none(self, tmp_path: Path) -> None:
        cache = VerificationCache(tmp_path / "c.sqlite")
        assert cache.get("ird", "12345678", "context") is None

    def test_overwrite_same_key(self, tmp_path: Path) -> None:
        cache = VerificationCache(tmp_path / "c.sqlite")
        a = VerificationResult(verdict=Verdict.CONFIRMED, confidence=0.9, reason="a")
        b = VerificationResult(verdict=Verdict.REJECTED, confidence=0.4, reason="b")
        cache.put("ird", "x", "ctx", a)
        cache.put("ird", "x", "ctx", b)
        got = cache.get("ird", "x", "ctx")
        assert got is not None
        assert got.verdict is Verdict.REJECTED


# ---------------------------------------------------------------------------
# GeminiVerifier with a mocked client
# ---------------------------------------------------------------------------


class _FakeClient:
    """Stub that mimics ``google.genai.Client``.

    Stores call count + lets the test fix a canned text response or raise.
    """

    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self._text = text
        self._error = error
        self.calls: list[dict[str, Any]] = []

        outer = self

        class _Models:
            def generate_content(self, *, model: str, contents: str) -> Any:
                outer.calls.append({"model": model, "contents": contents})
                if outer._error is not None:
                    raise outer._error
                return SimpleNamespace(text=outer._text)

        self.models = _Models()


class TestGeminiVerifier:
    def test_confirmed_verdict_parsed(self, tmp_path: Path) -> None:
        client = _FakeClient(
            text='{"verdict": "confirmed", "confidence": 0.92, "reason": "looks legit"}'
        )
        v = GeminiVerifier(cache_path=tmp_path / "c.sqlite", client=client)
        result = v.verify("driver_licence", "BQ739482", "Driver licence BQ739482")
        assert result.verdict is Verdict.CONFIRMED
        assert result.confidence == pytest.approx(0.92)
        assert result.cached is False
        v.close()

    def test_response_with_markdown_fence(self, tmp_path: Path) -> None:
        client = _FakeClient(
            text='```json\n{"verdict": "rejected", "confidence": 0.7, "reason": "SKU"}\n```'
        )
        v = GeminiVerifier(cache_path=tmp_path / "c.sqlite", client=client)
        result = v.verify("driver_licence", "BQ739482", "SKU BQ739482")
        assert result.verdict is Verdict.REJECTED
        v.close()

    def test_cache_hit_skips_client(self, tmp_path: Path) -> None:
        client = _FakeClient(text='{"verdict": "confirmed", "confidence": 0.9, "reason": "ok"}')
        v = GeminiVerifier(cache_path=tmp_path / "c.sqlite", client=client)
        v.verify("ird", "49091850", "IRD 49091850")
        v.verify("ird", "49091850", "IRD 49091850")  # second call: cache hit
        assert len(client.calls) == 1
        v.close()

    def test_429_raises_quota_exceeded(self, tmp_path: Path) -> None:
        client = _FakeClient(error=RuntimeError("API error 429: quota exceeded"))
        v = GeminiVerifier(cache_path=tmp_path / "c.sqlite", client=client)
        with pytest.raises(QuotaExceededError):
            v.verify("driver_licence", "BQ739482", "ctx")
        v.close()

    def test_generic_error_returns_uncertain(self, tmp_path: Path) -> None:
        client = _FakeClient(error=RuntimeError("transient parse blip"))
        v = GeminiVerifier(cache_path=tmp_path / "c.sqlite", client=client)
        result = v.verify("driver_licence", "BQ739482", "ctx")
        assert result.verdict is Verdict.UNCERTAIN
        v.close()


# ---------------------------------------------------------------------------
# apply_verification re-scoring
# ---------------------------------------------------------------------------


class _ScriptedVerifier:
    """Returns canned verdicts per (detector, value) tuple for unit tests."""

    def __init__(self, mapping: dict[tuple[str, str], VerificationResult]) -> None:
        self.mapping = mapping
        self.calls: list[tuple[str, str]] = []

    def verify(self, detector: str, value: str, context: str) -> VerificationResult:
        self.calls.append((detector, value))
        return self.mapping[(detector, value)]


class TestApplyVerification:
    def test_only_low_confidence_findings_verified(self) -> None:
        df = pd.DataFrame(
            {
                "note": [
                    "IRD on file: 49091850 (high confidence, checksum-valid)",
                    "Reference BQ739482 (low confidence, no keyword)",
                ]
            }
        )
        result = Scanner().scan_dataframe(df)
        # Sanity: there should be at least one high-confidence (IRD) and one
        # low-confidence (driver_licence shape-only) finding.
        assert any(cf.finding.confidence >= 0.8 for cf in result.findings)
        assert any(cf.finding.confidence < 0.8 for cf in result.findings)

        verifier = _ScriptedVerifier(
            {
                ("driver_licence", "BQ739482"): VerificationResult(
                    verdict=Verdict.REJECTED, confidence=0.9, reason="SKU"
                ),
            }
        )
        verified = apply_verification(result, verifier, threshold=0.8)

        # Driver licence finding was rejected -> dropped.
        detectors_remaining = {cf.finding.detector for cf in verified.findings}
        assert "driver_licence" not in detectors_remaining
        # IRD finding was above threshold -> not verified, still present.
        assert "ird" in detectors_remaining
        # Only the one low-confidence finding was sent to the verifier.
        assert verifier.calls == [("driver_licence", "BQ739482")]

    def test_confirmed_promotes_confidence(self) -> None:
        df = pd.DataFrame({"note": ["Reference BQ739482 follows"]})
        result = Scanner().scan_dataframe(df)
        verifier = _ScriptedVerifier(
            {
                ("driver_licence", "BQ739482"): VerificationResult(
                    verdict=Verdict.CONFIRMED, confidence=0.92, reason="legit"
                ),
            }
        )
        verified = apply_verification(result, verifier, threshold=0.8)
        dl = [cf for cf in verified.findings if cf.finding.detector == "driver_licence"]
        assert len(dl) == 1
        assert dl[0].finding.confidence >= 0.95
        assert dl[0].finding.context["verified"] is True
        assert dl[0].finding.context["llm_verdict"] == "confirmed"

    def test_uncertain_keeps_original(self) -> None:
        df = pd.DataFrame({"note": ["Reference BQ739482 follows"]})
        result = Scanner().scan_dataframe(df)
        original_conf = next(
            cf.finding.confidence
            for cf in result.findings
            if cf.finding.detector == "driver_licence"
        )
        verifier = _ScriptedVerifier(
            {
                ("driver_licence", "BQ739482"): VerificationResult(
                    verdict=Verdict.UNCERTAIN, confidence=0.5, reason="ambiguous"
                ),
            }
        )
        verified = apply_verification(result, verifier, threshold=0.8)
        dl = [cf for cf in verified.findings if cf.finding.detector == "driver_licence"]
        assert len(dl) == 1
        # Confidence unchanged, but context annotated.
        assert dl[0].finding.confidence == pytest.approx(original_conf)
        assert dl[0].finding.context["verified"] is True
        assert dl[0].finding.context["llm_verdict"] == "uncertain"
