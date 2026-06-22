"""NZ address detector.

Address detection combines three signals to flag values that look like a
New Zealand street address:

1. **Street-suffix shape** — a numeric prefix followed by 1\u20134 words and a
   recognised NZ street-type suffix (``Street``, ``Road``, ``Avenue``,
   ``Drive``, ``Lane``, etc., and their common abbreviations).
2. **NZ postcode** — a 4-digit token (NZ Post uses 4-digit postcodes).
   This is only confirmatory; bare 4-digit tokens are too common to flag
   on their own.
3. **NZ location name** \u2014 one of the 16 regions, major cities, or common
   metropolitan suburbs from the bundled gazetteer.

Severity is ``MEDIUM`` because an address is a quasi-identifier under
the Privacy Act 2020 \u2014 it does not necessarily identify a natural
person on its own, but combines readily with other attributes to do so.

Confidence scales with the number of corroborating signals:

- 0.5 \u2014 street-suffix shape only
- 0.7 \u2014 street-suffix shape + postcode OR location
- 0.9 \u2014 street-suffix shape + postcode + location
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .base import Detector, Finding, Severity

# Street-type suffixes commonly used in NZ. Stored in lowercase for the
# regex; the regex itself is case-insensitive. Order doesn't affect
# matching since the alternation uses literal text.
_STREET_SUFFIXES = (
    # Full forms
    "street",
    "road",
    "avenue",
    "drive",
    "lane",
    "place",
    "crescent",
    "terrace",
    "boulevard",
    "highway",
    "court",
    "close",
    "parade",
    "mall",
    "quay",
    "square",
    "loop",
    "rise",
    "grove",
    "way",
    "heights",
    "park",
    "esplanade",
    "promenade",
    # Abbreviations
    "st",
    "rd",
    "ave",
    "av",
    "dr",
    "ln",
    "pl",
    "cres",
    "tce",
    "blvd",
    "hwy",
    "ct",
    "cl",
    "pde",
    "sq",
)

# NZ regions, major cities, and a selection of common metropolitan suburbs.
# This gazetteer is intentionally compact to keep the detector lightweight;
# it can be extended with a fuller NZ Post suburb list in a later release.
_NZ_LOCATIONS: frozenset[str] = frozenset(
    {
        # 16 regions
        "Northland",
        "Auckland",
        "Waikato",
        "Bay of Plenty",
        "Gisborne",
        "Hawke's Bay",
        "Hawkes Bay",
        "Taranaki",
        "Manawatu-Whanganui",
        "Manawat\u016b-Whanganui",
        "Wellington",
        "Tasman",
        "Nelson",
        "Marlborough",
        "West Coast",
        "Canterbury",
        "Otago",
        "Southland",
        # Major cities / towns
        "Whangarei",
        "Whang\u0101rei",
        "Hamilton",
        "Tauranga",
        "Rotorua",
        "Taupo",
        "Taup\u014d",
        "Napier",
        "Hastings",
        "New Plymouth",
        "Palmerston North",
        "Whanganui",
        "Lower Hutt",
        "Upper Hutt",
        "Porirua",
        "Kapiti",
        "K\u0101piti",
        "Blenheim",
        "Greymouth",
        "Christchurch",
        "Timaru",
        "Dunedin",
        "Queenstown",
        "Invercargill",
        # Common Auckland suburbs
        "Albany",
        "Botany",
        "Devonport",
        "Epsom",
        "Glenfield",
        "Grey Lynn",
        "Henderson",
        "Howick",
        "Manukau",
        "Mt Albert",
        "Mt Eden",
        "Mount Albert",
        "Mount Eden",
        "Newmarket",
        "North Shore",
        "Onehunga",
        "Otahuhu",
        "Ot\u0101huhu",
        "Pakuranga",
        "Papakura",
        "Papatoetoe",
        "Parnell",
        "Ponsonby",
        "Remuera",
        "Takapuna",
        # Common Wellington suburbs
        "Brooklyn",
        "Karori",
        "Kelburn",
        "Khandallah",
        "Miramar",
        "Newtown",
        "Petone",
        "Thorndon",
        # Common Christchurch suburbs
        "Addington",
        "Fendalton",
        "Hornby",
        "Ilam",
        "Linwood",
        "Merivale",
        "Papanui",
        "Riccarton",
        "Sumner",
        "Sydenham",
    }
)

# Build a case-insensitive alternation, longest first so multi-word
# locations like "Bay of Plenty" match before "Bay" alone would.
_LOCATION_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(re.escape(loc) for loc in sorted(_NZ_LOCATIONS, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)

# 4-digit NZ postcode. NZ Post issues postcodes in 0110-9999; values
# below 0100 are unused.
_POSTCODE_PATTERN = re.compile(r"\b(0[1-9]\d{2}|[1-9]\d{3})\b")

# Street-shape: optional unit prefix (e.g. "5/" or "Apt 12,"), street
# number with optional trailing letter (e.g. "12A"), 1-4 capitalised
# words, then a recognised suffix. Allows hyphens within street names
# (e.g. "Karangahape" or "Tirau-Putaruru").
_SUFFIX_GROUP = "|".join(_STREET_SUFFIXES)
_ADDRESS_PATTERN = re.compile(
    rf"""
    \b
    (
        (?:\d+\s*/\s*)?                 # optional unit prefix like "5/"
        \d{{1,5}}[A-Za-z]?               # street number, optional unit letter
        \s+
        (?:[A-Z][A-Za-z\u00C0-\u017F\u0100-\u017F'\u2019\u014c\u014d]*[-\s]){{1,4}}
        (?:{_SUFFIX_GROUP})
    )
    \b
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _supporting_signals(value: str, address_start: int, address_end: int) -> list[str]:
    """Find postcode and NZ-location signals OUTSIDE the address span."""
    signals: list[str] = []
    for pc in _POSTCODE_PATTERN.finditer(value):
        if pc.start() >= address_start and pc.end() <= address_end:
            continue
        signals.append(f"postcode:{pc.group()}")
        break
    for loc in _LOCATION_PATTERN.finditer(value):
        if loc.start() >= address_start and loc.end() <= address_end:
            continue
        signals.append(f"location:{loc.group()}")
        break
    return signals


def _confidence_for(signals: list[str]) -> float:
    has_postcode = any(s.startswith("postcode:") for s in signals)
    has_location = any(s.startswith("location:") for s in signals)
    if has_postcode and has_location:
        return 0.9
    if has_postcode or has_location:
        return 0.7
    return 0.5


class AddressDetector(Detector):
    """Detects NZ street addresses via shape + postcode + gazetteer signals.

    Emits a finding for each street-shape match. Confidence reflects how
    many corroborating signals (postcode, NZ region / city / suburb) are
    present in the same value.
    """

    name = "address"
    severity = Severity.MEDIUM

    def scan(self, value: str) -> Iterable[Finding]:
        for match in _ADDRESS_PATTERN.finditer(value):
            raw = match.group(1).strip()
            signals = _supporting_signals(value, match.start(1), match.end(1))
            yield Finding(
                detector=self.name,
                severity=self.severity,
                value=raw,
                start=match.start(1),
                end=match.end(1),
                confidence=_confidence_for(signals),
                context={"signals": signals},
            )
