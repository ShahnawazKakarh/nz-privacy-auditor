"""Tests for the NHI detector.

Test vectors are drawn from Health NZ | Te Whatu Ora's published examples
of the legacy (AAANNNC) and new (AAANNAX) NHI formats. These identifiers
appear in the public format-change documentation and are not real
patient NHIs.
"""

from __future__ import annotations

import pytest

from nz_privacy_auditor.detectors.nhi import NHIDetector, is_valid_nhi

# Legacy format examples from Health NZ NHI format-change documentation.
# These are sequential allocations used as worked examples.
VALID_LEGACY = ["ZAA0067", "ZAA0075", "ZAA0083"]

# New-format examples from Health NZ format-change documentation (issued
# randomly from 1 July 2026 onwards).
VALID_NEW = ["ACA31FM", "ASE37QK", "ARE62RS"]

INVALID_NHIS = [
    "ZAA0068",  # legacy with corrupted check digit
    "ZAA0076",  # legacy with corrupted check digit
    "ACA31FN",  # new with corrupted check letter
    "ABC1234",  # plausible legacy shape but wrong checksum
    "AIA0067",  # contains I (excluded letter)
    "AOA0067",  # contains O (excluded letter)
    "ABCD123",  # 4 letters + 3 digits (wrong shape)
    "ABC123",  # too short
    "ABC12345",  # too long
    "",  # empty
]


class TestChecksum:
    @pytest.mark.parametrize("nhi", VALID_LEGACY)
    def test_valid_legacy_passes(self, nhi: str) -> None:
        assert is_valid_nhi(nhi) is True

    @pytest.mark.parametrize("nhi", VALID_NEW)
    def test_valid_new_passes(self, nhi: str) -> None:
        assert is_valid_nhi(nhi) is True

    @pytest.mark.parametrize("nhi", INVALID_NHIS)
    def test_invalid_fails(self, nhi: str) -> None:
        assert is_valid_nhi(nhi) is False

    def test_lowercase_accepted(self) -> None:
        # is_valid_nhi normalises case before validating.
        assert is_valid_nhi("zaa0067") is True
        assert is_valid_nhi("aca31fm") is True


class TestDetector:
    def setup_method(self) -> None:
        self.detector = NHIDetector()

    def test_finds_legacy_nhi(self) -> None:
        findings = list(self.detector.scan("Patient NHI ZAA0067 admitted."))
        assert len(findings) == 1
        f = findings[0]
        assert f.value == "ZAA0067"
        assert f.context["format"] == "legacy"
        assert f.confidence == 1.0

    def test_finds_new_format_nhi(self) -> None:
        findings = list(self.detector.scan("Patient NHI ACA31FM admitted."))
        assert len(findings) == 1
        f = findings[0]
        assert f.context["format"] == "new"

    def test_ignores_invalid_checksum(self) -> None:
        findings = list(self.detector.scan("Reference ABC1234"))
        assert findings == []

    def test_ignores_letters_with_io(self) -> None:
        # Letters I and O are excluded from the NHI alphabet, so the
        # regex should reject them.
        findings = list(self.detector.scan("Reference AIA0067 AOA0067"))
        assert findings == []

    def test_no_match_in_plain_text(self) -> None:
        findings = list(self.detector.scan("This sentence has no NHI."))
        assert findings == []

    def test_offsets_correct(self) -> None:
        text = "NHI is ZAA0067 here"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        f = findings[0]
        assert text[f.start : f.end] == "ZAA0067"

    def test_multiple_nhis_in_one_value(self) -> None:
        text = "Old NHI ZAA0067, new NHI ACA31FM."
        findings = list(self.detector.scan(text))
        assert len(findings) == 2
        normalised = {f.context["normalised"] for f in findings}
        formats = {f.context["format"] for f in findings}
        assert normalised == {"ZAA0067", "ACA31FM"}
        assert formats == {"legacy", "new"}

    def test_case_insensitive_match(self) -> None:
        findings = list(self.detector.scan("nhi zaa0067 lowercase"))
        assert len(findings) == 1
        assert findings[0].context["normalised"] == "ZAA0067"
