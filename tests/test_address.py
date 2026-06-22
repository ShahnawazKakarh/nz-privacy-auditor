"""Tests for the NZ address detector.

Covers street-suffix shape detection across full and abbreviated suffixes,
unit prefixes, and confidence scaling based on supporting signals
(postcode, NZ region / city / suburb gazetteer).
"""

from __future__ import annotations

from nz_privacy_auditor.detectors.address import AddressDetector


class TestDetector:
    def setup_method(self) -> None:
        self.detector = AddressDetector()

    def test_finds_full_address(self) -> None:
        text = "She lives at 12 Queen Street, Auckland 1010."
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        f = findings[0]
        assert f.value == "12 Queen Street"
        assert f.confidence == 0.9
        signals = f.context["signals"]
        assert any(s.startswith("postcode:1010") for s in signals)
        assert any(s.startswith("location:Auckland") for s in signals)

    def test_address_with_postcode_only(self) -> None:
        text = "Send the package to 45 King Road, 1010."
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        assert findings[0].confidence == 0.7

    def test_address_with_location_only(self) -> None:
        text = "Office at 200 Lambton Quay, Wellington."
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        f = findings[0]
        assert f.confidence == 0.7
        assert any("location:Wellington" in s for s in f.context["signals"])

    def test_address_shape_only(self) -> None:
        text = "Property at 100 Manukau Road."
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        assert findings[0].confidence == 0.5

    def test_abbreviated_suffix(self) -> None:
        text = "5 Oxford St, Christchurch"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        f = findings[0]
        assert f.value == "5 Oxford St"
        assert any("location:Christchurch" in s for s in f.context["signals"])

    def test_unit_prefix(self) -> None:
        text = "5/123 Karangahape Road, Auckland"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        # The shape match begins at the unit prefix.
        assert findings[0].value.endswith("Karangahape Road")

    def test_unit_letter_suffix(self) -> None:
        text = "12A Manukau Road"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        assert findings[0].value == "12A Manukau Road"

    def test_multi_word_street_name(self) -> None:
        text = "1 Sir Edmund Hillary Drive, Auckland"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        f = findings[0]
        assert "Sir Edmund Hillary Drive" in f.value

    def test_multiple_addresses(self) -> None:
        text = "From 1 Queen Street to 99 King Road in Auckland."
        findings = list(self.detector.scan(text))
        assert len(findings) == 2
        values = {f.value for f in findings}
        assert "1 Queen Street" in values
        assert "99 King Road" in values

    def test_no_match_in_plain_text(self) -> None:
        text = "This sentence does not contain an address."
        findings = list(self.detector.scan(text))
        assert findings == []

    def test_offsets_correct(self) -> None:
        text = "Send to 12 Queen Street tomorrow"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        f = findings[0]
        assert text[f.start : f.end] == "12 Queen Street"

    def test_postcode_inside_address_not_counted(self) -> None:
        # The leading "1010" here is the street number, not a postcode.
        text = "1010 Great North Road"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        # Confidence stays 0.5 (no external postcode signal).
        assert findings[0].confidence == 0.5

    def test_region_signal(self) -> None:
        text = "Office at 50 Riverside Drive, Hawke's Bay"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        signals = findings[0].context["signals"]
        assert any("location:Hawke's Bay" in s for s in signals)
