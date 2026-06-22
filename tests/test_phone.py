"""Tests for the NZ phone detector.

Covers the four phone-kind classifications (mobile, landline, toll-free,
premium) across international and national formats, with various
separator styles (spaces, hyphens, parentheses).
"""

from __future__ import annotations

import pytest

from nz_privacy_auditor.detectors.phone import PhoneDetector, to_e164

# (raw, expected_e164, expected_kind)
VALID_PHONES = [
    # Mobile — international and national, various separators
    ("+64 21 123 4567", "+64211234567", "mobile"),
    ("+64-27-555-1234", "+64275551234", "mobile"),
    ("0064 22 987 6543", "+64229876543", "mobile"),
    ("021 123 4567", "+64211234567", "mobile"),
    ("027-555-1234", "+64275551234", "mobile"),
    ("0211234567", "+64211234567", "mobile"),
    # Landline — Auckland (09), Wellington (04), South Island (03), upper N (07), lower N (06)
    ("+64 9 700 1234", "+6497001234", "landline"),
    ("09 700 1234", "+6497001234", "landline"),
    ("(09) 700 1234", "+6497001234", "landline"),
    ("03 123 4567", "+6431234567", "landline"),
    ("04 555 1234", "+6445551234", "landline"),
    ("07 123 4567", "+6471234567", "landline"),
    # Toll-free
    ("0800 123 456", "+64800123456", "toll_free"),
    ("0508 123 456", "+64508123456", "toll_free"),
    # Premium
    ("0900 12345", "+6490012345", "premium"),
]

INVALID_PHONES = [
    "123-456-7890",  # US format
    "12345678",  # bare 8 digits no prefix
    "+1 555 123 4567",  # US international
    "0",  # too short
    "+64",  # too short
    "01 234 5678",  # NSN starts with 1 — not a valid NZ prefix
    "05 555 1234",  # NSN starts with 5 alone (not 508) — invalid
]


class TestE164:
    @pytest.mark.parametrize("raw,expected,_", VALID_PHONES)
    def test_valid_to_e164(self, raw: str, expected: str, _: str) -> None:
        assert to_e164(raw) == expected

    @pytest.mark.parametrize("raw", INVALID_PHONES)
    def test_invalid_to_e164(self, raw: str) -> None:
        assert to_e164(raw) is None


class TestDetector:
    def setup_method(self) -> None:
        self.detector = PhoneDetector()

    @pytest.mark.parametrize("raw,expected_e164,expected_kind", VALID_PHONES)
    def test_finds_valid_phones(self, raw: str, expected_e164: str, expected_kind: str) -> None:
        text = f"Call me on {raw} after work."
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        f = findings[0]
        assert f.context["e164"] == expected_e164
        assert f.context["kind"] == expected_kind
        assert f.detector == "phone"

    def test_country_code_higher_confidence(self) -> None:
        intl = next(self.detector.scan("Call +64 21 123 4567"))
        national = next(self.detector.scan("Call 021 123 4567"))
        assert intl.confidence == 1.0
        assert national.confidence == 0.8

    @pytest.mark.parametrize("raw", INVALID_PHONES)
    def test_ignores_invalid(self, raw: str) -> None:
        findings = list(self.detector.scan(f"Reference {raw} here."))
        assert findings == []

    def test_finds_multiple_phones(self) -> None:
        text = "Reach us at 021 123 4567 or 0800 123 456 anytime."
        findings = list(self.detector.scan(text))
        assert len(findings) == 2
        kinds = {f.context["kind"] for f in findings}
        assert kinds == {"mobile", "toll_free"}

    def test_offsets_correct(self) -> None:
        text = "My number is 021 123 4567 thanks"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        f = findings[0]
        assert text[f.start : f.end] == "021 123 4567"

    def test_no_match_in_plain_text(self) -> None:
        findings = list(self.detector.scan("There is no phone number here."))
        assert findings == []
