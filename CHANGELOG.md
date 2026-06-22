# Changelog

All notable changes to this project will be documented in this file. Format roughly follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **NZ phone detector** — recognises NZ phone numbers in international (`+64`, `0064`) and national (`0` trunk) formats with permissive separators (spaces, hyphens, dots, parentheses). The detector strips separators and prefixes, then validates the National Significant Number against the New Zealand Numbering Plan: mobile (`2X`, NSN 8–10 digits), geographic landline (areas 3, 4, 6, 7, 9; NSN 8 digits), toll-free (`0800`, `0508`; NSN 9–10 digits), and premium-rate (`0900`; NSN 8–9 digits). Findings carry the canonical E.164 form and the phone-kind label. Confidence is 1.0 with an explicit country code and 0.8 for national-form matches. Severity is MEDIUM (quasi-identifier under the Privacy Act 2020). Exposes a `to_e164()` helper for downstream normalisation.

- **Driver licence detector** — recognises NZ Waka Kotahi | NZ Transport Agency driver licence numbers in the format `[A-Z]{2}\d{6}` (e.g. `BQ739482`). NZTA does not publish a check-digit algorithm, so the detector applies a 300-character keyword-proximity heuristic (matching the Microsoft Purview NZ DLP rule): findings near keywords *licence*, *license*, *driver*, *DL* (uppercase), *NZTA*, or *Waka Kotahi* receive confidence 0.9; bare pattern matches receive confidence 0.5. 12 tests covering keyword variants, proximity boundary, case sensitivity, and shape rejection.

- **NHI (National Health Index) detector** — recognises both the legacy `AAANNNC` (mod-11 numeric check digit) and new `AAANNAX` (mod-23 alphabetic check digit) formats per HISO 10046:2024. Uses the 24-letter NHI alphabet (A–Z excluding I and O) with weights `(7, 6, 5, 4, 3, 2)`. Only checksum-validated matches are emitted. Test vectors drawn from Health NZ \| Te Whatu Ora's published format-change examples (`ZAA0067`, `ZAA0075`, `ZAA0083` for legacy; `ACA31FM`, `ASE37QK`, `ARE62RS` for new). Case-insensitive matching with normalised uppercase in the finding context.

### Planned

- NZ address detector (street suffix + suburb / region gazetteer).
- Te reo Māori name detector (macron-aware NER + curated name list).
- LLM verification pass (Gemini 2.5 Flash) for ambiguous spans.
- Loaders for CSV, Parquet, and HuggingFace datasets.
- CLI: `nz-privacy-auditor scan path/to/data.csv`.
- HTML + JSON compliance report.

## [0.1.0] — 2026-06-22

Initial scaffold and first detector.

### Added

- `src/` layout package built with [hatchling](https://hatch.pypa.io/).
- `Detector` ABC, `Finding` dataclass, `Severity` enum in `nz_privacy_auditor.detectors.base`.
- **IRD (Inland Revenue) detector** — regex match for 8/9-digit numbers (plain, hyphen-separated, space-separated) with mod-11 checksum validation per Inland Revenue's published algorithm. Uses the primary weight set with secondary-weight fallback, and enforces an issued-range bound of 10,000,000 – 150,000,000. Only checksum-validated matches are emitted, eliminating regex false positives.
- Test suite: 17 tests covering checksum correctness against IR worked-example vectors (`49091850`, `35901981`, `136410132`), 7 invalid-checksum / out-of-range / malformed cases, and 7 detector-behaviour cases (plain, hyphenated, spaced, multi-match, offset correctness).
- Project metadata in `pyproject.toml` with optional extras: `[ner]` (spaCy), `[llm]` (google-genai), `[hf]` (datasets), `[dev]` (pytest, ruff, mypy), `[all]`.
- Ruff configuration for lint + format.
- GitHub Actions CI: ruff lint + pytest on Python 3.11 and 3.12.
- Pre-commit hooks for ruff and basic file hygiene.

[Unreleased]: https://github.com/ShahnawazKakarh/nz-privacy-auditor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ShahnawazKakarh/nz-privacy-auditor/releases/tag/v0.1.0
