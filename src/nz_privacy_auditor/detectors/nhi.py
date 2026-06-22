"""NHI (National Health Index) number detector.

NZ NHI numbers are 7-character alphanumeric identifiers issued by Health NZ
| Te Whatu Ora. Two formats coexist:

1. **Legacy** (AAANNNC) — 3 letters + 3 digits + 1 numeric check digit.
   Validated with mod-11 checksum. Used since 1993; remaining capacity
   exhausted by mid-2026.

2. **New** (AAANNAX) — 3 letters + 2 digits + 1 letter + 1 letter check
   digit. Validated with mod-23 checksum. Issued from 1 July 2026 onwards
   alongside the legacy format.

Both formats exclude the letters ``I`` and ``O`` (visually ambiguous with
``1`` and ``0``). Each allowed letter maps to an ordinal 1–24:

    A=1, B=2, C=3, D=4, E=5, F=6, G=7, H=8, J=9, K=10,
    L=11, M=12, N=13, P=14, Q=15, R=16, S=17, T=18, U=19,
    V=20, W=21, X=22, Y=23, Z=24

The checksum applies weights ``(7, 6, 5, 4, 3, 2)`` to the first six
characters of the identifier. For the legacy format the seventh
character is a numeric check digit; for the new format it is a letter
check digit. The mod-23 operator was adopted for the new format after
testing showed mod-24 failed an unacceptably high rate of single-
character substitutions (HISO 10046:2024).

References:
    https://en.wikipedia.org/wiki/NHI_Number
    https://www.tewhatuora.govt.nz/health-services-and-programmes/health-identity/national-health-index/upcoming-changes-nhi
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .base import Detector, Finding, Severity

# Letters allowed in NHIs: A–Z excluding I and O. Ordinal value = position
# within this 24-letter alphabet.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_LETTER_VALUE: dict[str, int] = {ch: idx + 1 for idx, ch in enumerate(_ALPHABET)}
_VALUE_LETTER: dict[int, str] = {v: k for k, v in _LETTER_VALUE.items()}

# Weights applied to the first six characters for both checksum variants.
_WEIGHTS = (7, 6, 5, 4, 3, 2)

# Combined regex: 3 letters then either 4 digits (legacy) or 2 digits + 2 letters (new).
# Word boundaries prevent partial matches inside longer alphanumeric runs.
_NHI_PATTERN = re.compile(
    r"\b([A-HJ-NP-Z]{3}(?:\d{4}|\d{2}[A-HJ-NP-Z]{2}))\b",
    re.IGNORECASE,
)


def _char_value(ch: str) -> int | None:
    """Return the numeric value of an NHI character, or None if invalid."""
    if ch.isdigit():
        return int(ch)
    return _LETTER_VALUE.get(ch)


def _weighted_sum(chars: str) -> int | None:
    """Sum the first six characters weighted by ``_WEIGHTS``.

    Returns None if any character is outside the NHI alphabet.
    """
    total = 0
    for ch, w in zip(chars[:6], _WEIGHTS, strict=True):
        val = _char_value(ch)
        if val is None:
            return None
        total += val * w
    return total


def _legacy_valid(nhi: str) -> bool:
    """Validate a 7-character legacy NHI (AAANNNC) via mod-11 checksum."""
    if len(nhi) != 7:
        return False
    if not nhi[:3].isalpha() or not nhi[3:].isdigit():
        return False
    if any(ch in "IO" for ch in nhi[:3]):
        return False

    total = _weighted_sum(nhi)
    if total is None:
        return False

    remainder = total % 11
    # Per HISO spec: remainder of zero yields no valid check digit.
    if remainder == 0:
        return False

    check = 11 - remainder
    if check == 10:
        check = 0
    return check == int(nhi[6])


def _new_valid(nhi: str) -> bool:
    """Validate a 7-character new-format NHI (AAANNAX) via mod-23 checksum."""
    if len(nhi) != 7:
        return False
    if not nhi[:3].isalpha() or not nhi[3:5].isdigit() or not nhi[5:].isalpha():
        return False
    if any(ch in "IO" for ch in nhi[:3] + nhi[5:]):
        return False

    total = _weighted_sum(nhi)
    if total is None:
        return False

    remainder = total % 23
    check_value = 23 - remainder
    # check_value falls in 1..23; map back to its NHI alphabet letter.
    expected = _VALUE_LETTER.get(check_value)
    return expected is not None and expected == nhi[6]


def is_valid_nhi(nhi: str) -> bool:
    """Return True if ``nhi`` is a valid NHI in either format."""
    nhi = nhi.upper()
    # Legacy: last four are all digits.
    if len(nhi) == 7 and nhi[3:].isdigit():
        return _legacy_valid(nhi)
    # New: positions 3–4 are digits, 5–6 are letters.
    if len(nhi) == 7 and nhi[3:5].isdigit() and nhi[5:].isalpha():
        return _new_valid(nhi)
    return False


class NHIDetector(Detector):
    """Detects NZ National Health Index numbers in both legacy and new formats.

    Only checksum-validated matches are emitted. NHI numbers are highly
    sensitive health identifiers under the Privacy Act 2020 and the Health
    Information Privacy Code 2020.
    """

    name = "nhi"
    severity = Severity.HIGH

    def scan(self, value: str) -> Iterable[Finding]:
        for match in _NHI_PATTERN.finditer(value):
            raw = match.group(1).upper()
            if is_valid_nhi(raw):
                fmt = "legacy" if raw[3:].isdigit() else "new"
                yield Finding(
                    detector=self.name,
                    severity=self.severity,
                    value=match.group(1),
                    start=match.start(1),
                    end=match.end(1),
                    confidence=1.0,
                    context={"normalised": raw, "format": fmt},
                )
