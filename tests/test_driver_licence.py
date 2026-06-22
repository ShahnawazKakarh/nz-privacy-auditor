"""Tests for the NZ driver licence detector.

NZTA does not publish a check-digit algorithm for driver licence numbers,
so these tests focus on the format pattern and on the keyword-proximity
confidence heuristic.

Test format examples (``BQ739482``, ``UE093153``) are commonly cited as
NZ driver licence shape examples in published documentation and DLP
dictionaries; they are not associated with any real licence holder.
"""

from __future__ import annotations

from nz_privacy_auditor.detectors.driver_licence import DriverLicenceDetector


class TestDetector:
    def setup_method(self) -> None:
        self.detector = DriverLicenceDetector()

    def test_finds_plain_licence(self) -> None:
        findings = list(self.detector.scan("My driver licence is BQ739482."))
        assert len(findings) == 1
        f = findings[0]
        assert f.value == "BQ739482"
        assert f.detector == "driver_licence"
        # Keyword "driver licence" is within proximity -> high confidence.
        assert f.confidence == 0.9
        assert f.context["keyword_proximity"] is True

    def test_low_confidence_without_keyword(self) -> None:
        # Plain pattern with no surrounding context keyword.
        findings = list(self.detector.scan("Reference code BQ739482 follows."))
        assert len(findings) == 1
        assert findings[0].confidence == 0.5
        assert findings[0].context["keyword_proximity"] is False

    def test_uppercase_dl_keyword_boosts(self) -> None:
        findings = list(self.detector.scan("DL: BQ739482"))
        assert len(findings) == 1
        assert findings[0].confidence == 0.9

    def test_lowercase_dl_does_not_boost(self) -> None:
        # ``dl`` lower-case is the chemistry unit (decilitre) and should not
        # be treated as the driver-licence keyword.
        findings = list(self.detector.scan("dose 50dl reference BQ739482"))
        assert len(findings) == 1
        assert findings[0].confidence == 0.5

    def test_licen_se_spelling_boosts(self) -> None:
        # American spelling "license" must also trigger the keyword boost.
        findings = list(self.detector.scan("Driver license BQ739482 on file."))
        assert len(findings) == 1
        assert findings[0].confidence == 0.9

    def test_case_insensitive_match(self) -> None:
        findings = list(self.detector.scan("Licence bq739482 lowercase pattern"))
        assert len(findings) == 1
        assert findings[0].context["normalised"] == "BQ739482"

    def test_offsets_correct(self) -> None:
        text = "Driver licence BQ739482 issued."
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        f = findings[0]
        assert text[f.start : f.end] == "BQ739482"

    def test_multiple_licences(self) -> None:
        text = "Driver licences on file: BQ739482 and UE093153."
        findings = list(self.detector.scan(text))
        assert len(findings) == 2
        assert {f.value for f in findings} == {"BQ739482", "UE093153"}

    def test_ignores_wrong_shape(self) -> None:
        # One letter + 6 digits (too short)
        findings = list(self.detector.scan("Driver licence W421209."))
        assert findings == []

    def test_ignores_trailing_letter(self) -> None:
        # Two letters + 6 digits + trailing letter — \b should reject because
        # the trailing letter is still a word character.
        findings = list(self.detector.scan("Code W421209T follows."))
        assert findings == []

    def test_keyword_within_300_chars(self) -> None:
        # Keyword sits at the start; match sits ~200 chars later — still inside window.
        prefix = "Driver licence on file. " + ("x " * 100)
        text = prefix + "BQ739482"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        assert findings[0].confidence == 0.9

    def test_keyword_outside_300_chars(self) -> None:
        # Keyword sits well outside the 300-char window.
        prefix = "Driver licence on file. " + ("x " * 200)
        text = prefix + "BQ739482"
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        assert findings[0].confidence == 0.5
