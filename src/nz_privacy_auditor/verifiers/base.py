"""LLM verification interface and shared types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    """Outcome of an LLM second-pass review."""

    CONFIRMED = "confirmed"  # value is genuinely a member of the claimed PII class
    REJECTED = "rejected"  # value matches the regex shape but is not actually PII
    UNCERTAIN = "uncertain"  # not enough signal in the context to decide


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of verifying one finding."""

    verdict: Verdict
    confidence: float  # LLM's own confidence in the verdict, 0\u20131
    reason: str  # one-sentence rationale
    cached: bool = False  # True when the verdict was served from disk cache


# Short, human-readable description of each detector's claim, used in the prompt.
DETECTOR_DESCRIPTIONS: dict[str, str] = {
    "ird": "an NZ Inland Revenue (IRD) tax identification number",
    "nhi": "an NZ National Health Index (NHI) patient identifier",
    "driver_licence": "an NZ driver licence number issued by Waka Kotahi",
    "phone": "an NZ phone number",
    "address": "an NZ street address",
    "maori_name": "a te reo M\u0101ori personal name",
}


class LLMVerifier(ABC):
    """Abstract base for second-pass LLM verifiers."""

    @abstractmethod
    def verify(
        self,
        detector: str,
        value: str,
        context: str,
    ) -> VerificationResult:
        """Verify that ``value`` is genuinely an instance of the detector's claim.

        Args:
            detector: detector name (e.g. ``"driver_licence"``).
            value: the raw matched substring.
            context: the full cell value, providing surrounding context.
        """
        raise NotImplementedError
