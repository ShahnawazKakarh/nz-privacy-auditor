"""Tests for the te reo M\u0101ori name detector.

Covers macron-aware matching, multi-word names (e.g. ``Te Heuheu``,
``Te Aroha``), confidence based on macron preservation, and the kind
classification (given / surname / given_or_surname).
"""

from __future__ import annotations

from nz_privacy_auditor.detectors.maori_name import MaoriNameDetector


class TestDetector:
    def setup_method(self) -> None:
        self.detector = MaoriNameDetector()

    def test_finds_macron_preserved_name(self) -> None:
        findings = list(self.detector.scan("Kia ora, ahau ko T\u0101ne."))
        assert len(findings) == 1
        f = findings[0]
        assert f.value == "T\u0101ne"
        assert f.context["canonical"] == "T\u0101ne"
        assert f.context["macrons_preserved"] is True
        assert f.confidence == 0.9
        assert f.context["kind"] == "given"

    def test_finds_macron_stripped_name(self) -> None:
        # Same name without macron \u2014 still matched, lower confidence.
        findings = list(self.detector.scan("Hi Tane, welcome."))
        assert len(findings) == 1
        f = findings[0]
        assert f.value == "Tane"
        assert f.context["canonical"] == "T\u0101ne"
        assert f.context["macrons_preserved"] is False
        assert f.confidence == 0.7

    def test_finds_multi_word_name(self) -> None:
        findings = list(self.detector.scan("Speaker: Te Heuheu addressed the hui."))
        assert len(findings) == 1
        f = findings[0]
        assert f.value == "Te Heuheu"
        assert f.context["canonical"] == "Te Heuheu"
        assert f.context["kind"] == "surname"

    def test_case_insensitive_match(self) -> None:
        findings = list(self.detector.scan("aroha is a common name."))
        assert len(findings) == 1
        assert findings[0].context["canonical"] == "Aroha"

    def test_surname_classification(self) -> None:
        findings = list(self.detector.scan("Hon. Nanaia Mahuta"))
        assert len(findings) == 1
        f = findings[0]
        assert f.value == "Mahuta"
        assert f.context["kind"] == "surname"

    def test_given_and_surname_overlap(self) -> None:
        # Some entries (e.g. T\u0101mati, Paora, Tipene) appear in both lists.
        findings = list(self.detector.scan("Tipene attended the meeting."))
        assert len(findings) == 1
        assert findings[0].context["kind"] == "given_or_surname"

    def test_multiple_names_in_value(self) -> None:
        text = "Hosts were Aroha and Te Heuheu."
        findings = list(self.detector.scan(text))
        assert len(findings) == 2
        canonicals = {f.context["canonical"] for f in findings}
        assert canonicals == {"Aroha", "Te Heuheu"}

    def test_offsets_correct(self) -> None:
        text = "Speaker: T\u0101ne addressed everyone."
        findings = list(self.detector.scan(text))
        assert len(findings) == 1
        f = findings[0]
        assert text[f.start : f.end] == "T\u0101ne"

    def test_no_match_in_plain_text(self) -> None:
        findings = list(self.detector.scan("This sentence has no listed names."))
        assert findings == []

    def test_word_boundary_prevents_partial_match(self) -> None:
        # ``Tane`` should not match inside ``Octane``.
        findings = list(self.detector.scan("The Octane reading was high."))
        assert findings == []

    def test_macron_in_middle_of_name(self) -> None:
        # Wikit\u014dria has macron in the middle.
        findings = list(self.detector.scan("Wikit\u014dria is the queen."))
        assert len(findings) == 1
        f = findings[0]
        assert f.context["canonical"] == "Wikit\u014dria"
        assert f.confidence == 0.9

    def test_macron_in_middle_stripped(self) -> None:
        findings = list(self.detector.scan("Wikitoria is the queen."))
        assert len(findings) == 1
        f = findings[0]
        assert f.context["canonical"] == "Wikit\u014dria"
        assert f.confidence == 0.7
