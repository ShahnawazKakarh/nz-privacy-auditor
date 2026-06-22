"""NZ phone number detector.

New Zealand phone numbers follow the New Zealand Numbering Plan administered
by the Number Administration Deed (NAD). The country code is ``+64`` and the
domestic trunk prefix is ``0``. After stripping the country code and trunk
prefix, the National Significant Number (NSN) begins with one of:

- ``2X`` — mobile (021, 022, 024, 027, 028, 029 and other 02X blocks). NSN
  length 8–10 digits.
- ``3``, ``4``, ``6``, ``7``, ``9`` — single-digit geographic landline area
  codes (South Island, Wellington, Lower North Island, Central / Upper
  North Island, Auckland / Northland). NSN length 8 digits.
- ``800``, ``508`` — toll-free. NSN length 9–10 digits.
- ``900`` — premium-rate. NSN length 8–9 digits.

Severity is ``MEDIUM`` because a phone number alone is a quasi-identifier
under the Privacy Act 2020: it does not necessarily identify a natural
person on its own, but it readily combines with other attributes (name,
address) to do so.

References:
    https://en.wikipedia.org/wiki/Telephone_numbers_in_New_Zealand
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .base import Detector, Finding, Severity

# Loose match: international (+64 / 0064) form, or national (0) form.
# Allows spaces, hyphens, dots, and parentheses as separators.
_PHONE_PATTERN = re.compile(
    r"""
    (?<!\w)
    (
        (?:\+64|0064)[\s\-.()]{0,4}\d[\d\s\-.()]{6,14}\d   # international
        |
        0[\s\-.()]{0,3}\d[\d\s\-.()]{6,12}\d                # national
    )
    (?!\w)
    """,
    re.VERBOSE,
)


def _to_nsn(raw: str) -> str | None:
    """Strip separators and country / trunk prefixes to obtain the NSN.

    Returns the National Significant Number as a digit-only string, or
    None if the input cannot be reduced to a plausible NSN.
    """
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0064"):
        digits = digits[4:]
    elif digits.startswith("64") and len(digits) >= 10:
        # 64 + NSN (NSN is 8–10 digits, so total 10–12). Avoids stripping the
        # "64" out of, say, an Auckland landline beginning with "964…".
        digits = digits[2:]
    if digits.startswith("0"):
        digits = digits[1:]
    return digits or None


def _classify(nsn: str) -> str | None:
    """Return the phone-kind label for a valid NSN, or None if invalid."""
    if not nsn.isdigit():
        return None
    n = len(nsn)

    # Mobile: NSN begins with 2 and is 8–10 digits total.
    if nsn.startswith("2") and 8 <= n <= 10:
        return "mobile"

    # Toll-free / premium share length range with landline so check first.
    if (nsn.startswith("800") or nsn.startswith("508")) and 9 <= n <= 10:
        return "toll_free"
    if nsn.startswith("900") and 8 <= n <= 9:
        return "premium"

    # Geographic landline: single-digit area code 3, 4, 6, 7, or 9 then 7
    # subscriber digits, NSN = 8 digits.
    if n == 8 and nsn[0] in "34679":
        return "landline"

    return None


def to_e164(raw: str) -> str | None:
    """Return the canonical E.164 form for an NZ phone string, or None."""
    nsn = _to_nsn(raw)
    if nsn is None:
        return None
    if _classify(nsn) is None:
        return None
    return f"+64{nsn}"


class PhoneDetector(Detector):
    """Detects NZ phone numbers in international and national formats.

    Emits findings only for strings whose NSN, after stripping the country
    code and trunk prefix, matches a known prefix + length rule. Confidence
    is 1.0 for matches with an explicit ``+64`` or ``0064`` country code
    (unambiguously NZ) and 0.8 for national-form matches (which could
    occasionally be a non-NZ number using a leading 0 by coincidence).
    """

    name = "phone"
    severity = Severity.MEDIUM

    def scan(self, value: str) -> Iterable[Finding]:
        for match in _PHONE_PATTERN.finditer(value):
            raw = match.group(1)
            nsn = _to_nsn(raw)
            if nsn is None:
                continue
            kind = _classify(nsn)
            if kind is None:
                continue
            has_country_code = raw.startswith("+64") or raw.startswith("0064")
            yield Finding(
                detector=self.name,
                severity=self.severity,
                value=raw,
                start=match.start(1),
                end=match.end(1),
                confidence=1.0 if has_country_code else 0.8,
                context={
                    "e164": f"+64{nsn}",
                    "nsn": nsn,
                    "kind": kind,
                },
            )
