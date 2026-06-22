"""Gemini-backed :class:`LLMVerifier` (model ``gemini-2.5-flash``).

The verifier issues one classification call per finding, instructed to respond
with strict JSON. Results are cached on disk via :class:`VerificationCache`
so re-running the auditor on the same dataset is free.

Quota handling:
- The Gemini free tier limits requests per day (RPD); on a 429 the verifier
  raises :class:`QuotaExceededError` so the calling code can stop cleanly
  rather than retrying in a tight loop.
- All other errors fall back to a ``Verdict.UNCERTAIN`` result so a single
  bad call cannot abort an audit.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import (
    DETECTOR_DESCRIPTIONS,
    LLMVerifier,
    Verdict,
    VerificationResult,
)
from .cache import VerificationCache

if TYPE_CHECKING:
    from google.genai import Client


DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_CACHE_PATH = "data/llm_cache/cache.sqlite"


class QuotaExceededError(RuntimeError):
    """Raised when Gemini returns 429 (quota / rate limit exceeded)."""


_PROMPT_TEMPLATE = """\
You are a Privacy Act 2020 compliance assistant. A regex / heuristic detector
has flagged a candidate value as {description}. Decide whether the value is
genuinely an instance of that PII type IN ITS CONTEXT, or whether it merely
matches the shape (e.g. an SKU that looks like a driver-licence number).

Detector:   {detector}
Value:      "{value}"
Full cell:  "{context}"

Respond with ONLY a single JSON object on one line, no markdown, no commentary:
{{"verdict": "confirmed" | "rejected" | "uncertain", "confidence": <float 0..1>, "reason": "<one short sentence>"}}

Verdict meanings:
- confirmed: the value really is {description} in this context
- rejected:  the value matches the detector's shape but is clearly NOT {description}
- uncertain: cannot decide from the available context
"""


def _build_client(api_key: str | None = None) -> Client:
    """Construct a google-genai Client using GOOGLE_API_KEY by default."""
    try:
        from google import genai
    except ImportError as exc:
        raise ImportError(
            "google-genai is required for LLM verification. "
            "Install with: pip install 'nz-privacy-auditor[llm]'"
        ) from exc

    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Add it to a local .env file "
            "(see .env.example) and ensure python-dotenv has loaded it, "
            "or pass api_key= explicitly."
        )
    return genai.Client(api_key=key)


def _parse_response(text: str) -> tuple[Verdict, float, str]:
    """Parse the model's JSON response, tolerating common variations."""
    cleaned = text.strip()
    # Strip ```json fences if the model added them despite the instruction.
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(line for line in lines if not line.strip().startswith("```"))
    obj: dict[str, Any] = json.loads(cleaned)
    verdict = Verdict(str(obj["verdict"]).lower())
    confidence = float(obj.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))
    reason = str(obj.get("reason", "")).strip()
    return verdict, confidence, reason


class GeminiVerifier(LLMVerifier):
    """Gemini-backed LLM verifier with disk caching and clean 429 handling.

    Args:
        model: Gemini model id. Defaults to ``gemini-2.5-flash``.
        cache_path: SQLite cache file. Defaults to ``data/llm_cache/cache.sqlite``.
        api_key: Optional explicit key (otherwise read from ``GOOGLE_API_KEY``).
        client: Optional pre-constructed ``google.genai.Client`` (useful for tests).
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        cache_path: str | Path = DEFAULT_CACHE_PATH,
        api_key: str | None = None,
        client: Client | None = None,
    ) -> None:
        self.model = model
        self.cache = VerificationCache(cache_path)
        self._client = client if client is not None else _build_client(api_key)

    def verify(
        self,
        detector: str,
        value: str,
        context: str,
    ) -> VerificationResult:
        cached = self.cache.get(detector, value, context)
        if cached is not None:
            return cached

        prompt = _PROMPT_TEMPLATE.format(
            detector=detector,
            description=DETECTOR_DESCRIPTIONS.get(detector, "the claimed PII type"),
            value=value,
            context=context.replace('"', "'"),
        )

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            text = (response.text or "").strip()
            verdict, confidence, reason = _parse_response(text)
            result = VerificationResult(
                verdict=verdict,
                confidence=confidence,
                reason=reason,
                cached=False,
            )
        except QuotaExceededError:
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if "429" in msg or "quota" in msg or "rate" in msg:
                raise QuotaExceededError(str(exc)) from exc
            result = VerificationResult(
                verdict=Verdict.UNCERTAIN,
                confidence=0.5,
                reason=f"LLM error: {exc.__class__.__name__}",
                cached=False,
            )

        self.cache.put(detector, value, context, result)
        return result

    def close(self) -> None:
        self.cache.close()


__all__ = [
    "DEFAULT_CACHE_PATH",
    "DEFAULT_MODEL",
    "GeminiVerifier",
    "QuotaExceededError",
]
