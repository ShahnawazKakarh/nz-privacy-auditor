"""Tests for the IRD detector.

Test vectors are drawn from Inland Revenue's published algorithm worked
examples and from the public IR documentation on IRD number validation.
"""

from __future__ import annotations

import pytest
from nz_privacy_auditor.detectors.ird import IRDDetector, _checksum_ok

# IR-published worked examples from the official algorithm spec.
# These are known-valid IRD numbers used in IR's own validation examples;
# they are NOT issued to real taxpayers — they are spec test vectors.
VALID_IRDS = [
    "49091850",  # 8-digit form, IR primary-weights worked example
    "35901981",  # 8-digit form, IR secondary-weights worked example
    "136410132",  # 9-digit form, IR primary-weights worked example
]

# Tweak the check digit of each valid example by +1 (mod 10) to make it invalid.
INVALID_IRDS = [
    "49091851",
    "35901982",
    "136410133",
    "00000000",  # below MIN_IRD
    "999999999",  # above MAX_IRD
    "12345",  # wrong length
    "abcdefgh",  # non-numeric
]


class TestChecksum:
    @pytest.mark.parametrize("ird", VALID_IRDS)
    def test_valid_irds_pass_checksum(self, ird: str) -> None:
        assert _checksum_ok(ird) is True

    @pytest.mark.parametrize("ird", INVALID_IRDS)
    def test_invalid_irds_fail_checksum(self, ird: str) -> None:
        assert _checksum_ok(ird) is False


class TestDetector:
    def setup_method(self) -> None:
        self.detector = IRDDetector()

    def test_finds_plain_ird(self) -> None:
        findings = list(self.detector.scan("My IRD is 49091850 thanks"))
        assert len(findings) == 1
        assert findings[0].value == "49091850"
        assert findings[0].detector == "ird"
        assert findings[0].confidence == 1.0

    def test_finds_hyphenated_ird(self) -> None:
        findings = list(self.detector.scan("IRD: 49-091-850"))
        assert len(findings) == 1
        assert findings[0].context["normalised"] == "49091850"

    def test_finds_space_separated_ird(self) -> None:
        findings = list(self.detector.scan("IRD 136 410 132"))
        assert len(findings) == 1
        assert findings[0].context["normalised"] == "136410132"

    def test_ignores_invalid_checksum(self) -> None:
        # Looks like an IRD but fails mod-11
        findings = list(self.detector.scan("Number 12345678"))
        assert findings == []

    def test_no_match_in_plain_text(self) -> None:
        findings = list(self.detector.scan("This sentence has no IRD."))
        assert findings == []

    def test_offsets_correct(self) -> None:
        text = "IRD is 49091850 here"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        f = findings[0]
        assert text[f.start : f.end] == "49091850"

    def test_multiple_irds_in_one_value(self) -> None:
        text = "Old IRD 49091850, new IRD 136410132."
        findings = list(self.detector.scan(text))
        assert len(findings) == 2
        normalised = {f.context["normalised"] for f in findings}
        assert normalised == {"49091850", "136410132"}
