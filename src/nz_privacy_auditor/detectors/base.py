"""Base detector interface and shared types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """Severity of a Privacy Act 2020 finding.

    HIGH    — directly identifying, regulated identifiers (IRD, NHI, driver licence).
    MEDIUM  — quasi-identifiers that combine readily (phone, address).
    LOW     — context-sensitive signals (te reo names, generic name tokens).
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class Finding:
    """A single PII match within a value."""

    detector: str  # e.g. "ird", "nhi"
    severity: Severity
    value: str  # the matched substring (raw)
    start: int  # char offset within the source value
    end: int  # exclusive
    confidence: float = 1.0  # 0.0–1.0; 1.0 for checksum-verified
    context: dict = field(default_factory=dict)


class Detector(ABC):
    """Abstract base for all PII detectors.

    Implementations must be stateless and thread-safe — a single instance
    will be called across many rows / columns of a dataset.
    """

    name: str
    severity: Severity

    @abstractmethod
    def scan(self, value: str) -> Iterable[Finding]:
        """Yield findings for a single string value.

        Implementations should be tolerant of None / non-string input
        by guarding at the call site; this method assumes ``value`` is a str.
        """
        raise NotImplementedError
