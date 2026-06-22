"""IRD (Inland Revenue Department) number detector.

NZ IRD numbers are 8 or 9 digits with a mod-11 check digit. The algorithm
is published by Inland Revenue and uses a primary weight set, falling back
to a secondary weight set when the primary calculation yields a check
digit of 10.

Reference:
    https://www.ird.govt.nz/-/media/project/ir/home/documents/digital-service-providers/draft-documents/payday-filing/algorithm-for-ird-numbers.pdf

Valid IRD numbers fall between 10-000-000 and ~150-000-000. We use the
conservative upper bound of 150_000_000 to reject obviously out-of-range
candidates while remaining future-proof.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .base import Detector, Finding, Severity

# IRD numbers appear as 8 or 9 digit runs, optionally hyphen- or space-separated
# in groups like 49-091-850 or 49 091 850 or 049091850.
_IRD_PATTERN = re.compile(r"\b(\d{2,3}[-\s]?\d{3}[-\s]?\d{3})\b")

# Inland Revenue's published weight sets.
_PRIMARY_WEIGHTS = (3, 2, 7, 6, 5, 4, 3, 2)
_SECONDARY_WEIGHTS = (7, 4, 3, 2, 5, 2, 7, 6)

# IRD numbers below 10_000_000 are not issued.
_MIN_IRD = 10_000_000
# Upper sanity bound; IR is currently issuing in the 100M+ range.
_MAX_IRD = 150_000_000


def _checksum_ok(digits: str) -> bool:
    """Validate the mod-11 check digit for an 8- or 9-digit IRD string.

    ``digits`` must contain only digit characters. Returns True only when
    the IRD passes range and checksum validation.
    """
    if len(digits) not in (8, 9) or not digits.isdigit():
        return False

    # Left-pad 8-digit IRDs to 9 digits for uniform handling.
    padded = digits.zfill(9)
    body, check = padded[:8], int(padded[8])

    body_int = int(padded[:8] + padded[8])  # full number, for range check
    if not (_MIN_IRD <= body_int <= _MAX_IRD):
        return False

    def _calc(weights: tuple[int, ...]) -> int:
        total = sum(int(d) * w for d, w in zip(body, weights, strict=True))
        rem = total % 11
        if rem == 0:
            return 0
        return 11 - rem

    primary = _calc(_PRIMARY_WEIGHTS)
    if primary < 10:
        return primary == check

    # Primary produced 10 — fall back to secondary weights.
    secondary = _calc(_SECONDARY_WEIGHTS)
    if secondary == 10:
        # Number is invalid per IR spec.
        return False
    return secondary == check


class IRDDetector(Detector):
    """Detects NZ Inland Revenue (IRD) numbers via regex + mod-11 checksum.

    Only checksum-validated matches are emitted. The detector is stateless.
    """

    name = "ird"
    severity = Severity.HIGH

    def scan(self, value: str) -> Iterable[Finding]:
        for match in _IRD_PATTERN.finditer(value):
            raw = match.group(1)
            digits = re.sub(r"[-\s]", "", raw)
            if _checksum_ok(digits):
                yield Finding(
                    detector=self.name,
                    severity=self.severity,
                    value=raw,
                    start=match.start(1),
                    end=match.end(1),
                    confidence=1.0,
                    context={"normalised": digits},
                )
