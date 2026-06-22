"""NZ driver licence number detector.

New Zealand driver licence numbers are issued by Waka Kotahi | NZ Transport
Agency in the format ``[A-Z]{2}\\d{6}`` — two uppercase letters followed by
six digits, e.g. ``BQ739482`` or ``UE093153``. The licence number remains
the same when a new card is issued; the three-digit *card version number*
printed on the card is per-issue and is not detected by this module.

Unlike IRD and NHI numbers, NZTA does **not** publish a check-digit algorithm
for driver licence numbers. This means a regex alone produces many false
positives on dataset columns containing 2-letter prefixed codes (order IDs,
SKUs, flight references). To compensate, this detector lowers confidence
when no contextual keyword (``licence``, ``license``, ``driver``, ``DL``)
appears within a 300-character window of the match — the same approach
used by Microsoft Purview's NZ driver licence sensitive-information type.

Findings are emitted at confidence 0.9 when a keyword is nearby, and
confidence 0.5 otherwise. Downstream code may filter on confidence to
trade off precision against recall.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .base import Detector, Finding, Severity

# Two uppercase letters + six digits. Word boundaries to avoid partial
# matches inside longer alphanumeric runs.
_LICENCE_PATTERN = re.compile(r"\b([A-Z]{2}\d{6})\b", re.IGNORECASE)

# Context keywords. Case-insensitive whole-word match within the proximity
# window. ``DL`` is constrained to upper-case-only via a separate pattern
# below to avoid matching the common English word "dl" in chemistry / units.
_KEYWORD_PATTERN = re.compile(
    r"\b(?:licen[cs]e|driver(?:'?s)?|driver\s*licen[cs]e|driving\s*licen[cs]e|nzta|waka\s*kotahi)\b",
    re.IGNORECASE,
)
_DL_PATTERN = re.compile(r"\bDL\b")  # uppercase only

# Proximity window (chars) used to look for a contextual keyword around the
# matched licence-shaped token. Matches Microsoft Purview's NZ DLP setting.
_PROXIMITY = 300


def _has_keyword_near(value: str, start: int, end: int) -> bool:
    """Return True if a contextual keyword appears within the proximity window."""
    lo = max(0, start - _PROXIMITY)
    hi = min(len(value), end + _PROXIMITY)
    window = value[lo:hi]
    return bool(_KEYWORD_PATTERN.search(window) or _DL_PATTERN.search(window))


class DriverLicenceDetector(Detector):
    """Detects NZ driver licence numbers (``[A-Z]{2}\\d{6}``).

    Confidence is 0.9 when a contextual keyword (licence, license, driver,
    DL, NZTA, Waka Kotahi) is found within ±300 characters of the match,
    and 0.5 otherwise. There is no public NZTA checksum to validate against.
    """

    name = "driver_licence"
    severity = Severity.HIGH

    def scan(self, value: str) -> Iterable[Finding]:
        for match in _LICENCE_PATTERN.finditer(value):
            raw = match.group(1)
            has_kw = _has_keyword_near(value, match.start(1), match.end(1))
            yield Finding(
                detector=self.name,
                severity=self.severity,
                value=raw,
                start=match.start(1),
                end=match.end(1),
                confidence=0.9 if has_kw else 0.5,
                context={
                    "normalised": raw.upper(),
                    "keyword_proximity": has_kw,
                },
            )
