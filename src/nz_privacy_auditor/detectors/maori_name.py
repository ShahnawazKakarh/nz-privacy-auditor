"""Te reo M\u0101ori personal-name detector.

Detects predominantly M\u0101ori given names and surnames from a curated
gazetteer. The detector is **macron-aware**: a value like ``T\u0101ne`` and
its non-macron form ``Tane`` both match the canonical entry. Confidence
is higher (0.9) when the input preserved the macron \u2014 a signal that the
data was entered with cultural care \u2014 and lower (0.7) otherwise.

Severity is ``LOW`` because a personal name on its own is not necessarily
identifying under the Privacy Act 2020. The detector exists so that
downstream consumers can apply additional care to records that contain
culturally significant te reo M\u0101ori identifiers (e.g. IPP 4 collection
manner, IPP 8 accuracy obligations around name spelling and macron
preservation).

The gazetteer is intentionally focused on names that are predominantly
M\u0101ori. Strongly English-overlapping surnames (Davis, Smith, Williams,
Roberts, etc.) are excluded to avoid overwhelming auditors with false
positives. NER-based extension is planned in a future release.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from .base import Detector, Finding, Severity

# Curated te reo M\u0101ori given names. Canonical macron-preserved forms.
_GIVEN_NAMES: frozenset[str] = frozenset(
    {
        "Ahu",
        "Aotea",
        "Aroha",
        "Atareta",
        "Hahana",
        "Hana",
        "H\u0113nare",
        "H\u0113ni",
        "Hera",
        "Hineata",
        "Hinemoa",
        "Hinerangi",
        "Hineroa",
        "Hiwi",
        "H\u014dne",
        "Huia",
        "Iwa",
        "Kahu",
        "Kahukura",
        "Kahurangi",
        "Karanga",
        "Kataraina",
        "K\u0101hu",
        "Kawe",
        "Kura",
        "Maaka",
        "Maata",
        "Maia",
        "M\u0101kareta",
        "Manaaki",
        "Manawanui",
        "Manuwiri",
        "Maraea",
        "Marama",
        "Mareikura",
        "Matiu",
        "Matua",
        "M\u0101tauranga",
        "Mereana",
        "Mihaere",
        "Mihi",
        "Miriama",
        "Moana",
        "Naera",
        "Ngahere",
        "Ng\u0101huia",
        "Ngaire",
        "Ng\u0101moko",
        "Nikau",
        "Pania",
        "Paora",
        "Pare",
        "Patiti",
        "Peti",
        "Piripi",
        "Rahera",
        "Rangi",
        "Rangim\u0101rie",
        "Rapata",
        "R\u0101wiri",
        "R\u0113hia",
        "R\u0113weti",
        "Riria",
        "Riripeti",
        "Ruia",
        "T\u0101mati",
        "T\u0101ne",
        "Tangaroa",
        "Tangihia",
        "T\u0101whao",
        "T\u0101whirim\u0101tea",
        "Te Aroha",
        "Te Atat\u016b",
        "Te Rongo",
        "Tia",
        "Tipene",
        "Toi",
        "T\u016b\u012b",
        "Tui",
        "Waiora",
        "Wairaka",
        "Wairoa",
        "Waka",
        "Whaea",
        "Whaitiri",
        "Wikit\u014dria",
        "W\u012b",
    }
)

# Curated te reo M\u0101ori surnames. Canonical macron-preserved forms.
_SURNAMES: frozenset[str] = frozenset(
    {
        "Awarau",
        "Hawira",
        "Heihei",
        "Heke",
        "H\u0113nare",
        "Hirini",
        "Hokopaura",
        "Kaa",
        "Kaihau",
        "Kake",
        "Karena",
        "Karetai",
        "Kaumoana",
        "Kawana",
        "Mahuika",
        "Mahuta",
        "Mareikura",
        "Mikaere",
        "Ng\u0101moko",
        "Ng\u0101p\u014d",
        "Ngata",
        "Paora",
        "Parata",
        "Paringatai",
        "Pirini",
        "Pomare",
        "Rangihau",
        "Rangitaaua",
        "Rangit\u012bria",
        "Rapata",
        "Reedy",
        "Royal",
        "Sharples",
        "Tahere",
        "Tāmati",
        "Tamihere",
        "Tangohia",
        "Tapsell",
        "Taringa",
        "Tauwhare",
        "Te Aho",
        "Te Atawhai",
        "Te Heuheu",
        "Te Rangi",
        "Te Whaiti",
        "Te Whata",
        "Tinirau",
        "Tipene",
        "Tirikatene",
        "Toia",
        "Tureia",
        "Turia",
        "Uerata",
        "Waiariki",
        "Waipoua",
        "Waititi",
        "Wharepouri",
        "Whaitiri",
        "Witehira",
        "Witika",
    }
)

ALL_NAMES: frozenset[str] = _GIVEN_NAMES | _SURNAMES


def _fold(s: str) -> str:
    """Casefold and strip combining marks (macrons) for fuzzy matching."""
    nfd = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn").casefold()


# Pre-compute folded forms for O(1) lookup.
_FOLDED_TO_CANONICAL: dict[str, str] = {_fold(n): n for n in ALL_NAMES}

# Build the search regex. We match folded variants so the regex is
# essentially the union of all canonical and macron-stripped forms,
# sorted longest first so multi-word names like "Te Heuheu" win over "Te".
_NAME_VARIANTS = sorted(
    {n for n in ALL_NAMES} | {_fold(n) for n in ALL_NAMES},
    key=len,
    reverse=True,
)
_NAME_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(v) for v in _NAME_VARIANTS) + r")\b",
    re.IGNORECASE,
)


def _kind_for(canonical: str) -> str:
    if canonical in _GIVEN_NAMES and canonical in _SURNAMES:
        return "given_or_surname"
    if canonical in _GIVEN_NAMES:
        return "given"
    return "surname"


class MaoriNameDetector(Detector):
    """Detects te reo M\u0101ori personal names from a curated gazetteer.

    The detector is macron-aware and case-insensitive. Findings carry the
    canonical macron-preserved form in ``context['canonical']`` even when
    the input did not use macrons.
    """

    name = "maori_name"
    severity = Severity.LOW

    def scan(self, value: str) -> Iterable[Finding]:
        for match in _NAME_PATTERN.finditer(value):
            raw = match.group(0)
            canonical = _FOLDED_TO_CANONICAL.get(_fold(raw))
            if canonical is None:
                continue
            # Macron preservation is a strong cultural-care signal.
            macrons_preserved = raw.casefold() == canonical.casefold()
            yield Finding(
                detector=self.name,
                severity=self.severity,
                value=raw,
                start=match.start(),
                end=match.end(),
                confidence=0.9 if macrons_preserved else 0.7,
                context={
                    "canonical": canonical,
                    "kind": _kind_for(canonical),
                    "macrons_preserved": macrons_preserved,
                },
            )
