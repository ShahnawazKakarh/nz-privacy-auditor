# Changelog

All notable changes to this project will be documented in this file. Format roughly follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned

- NHI (National Health Index) detector with mod-11 checksum (legacy `[A-Z]{3}\d{4}` and new `[A-Z]{3}\d{3}[A-Z0-9]` formats).
- NZ driver licence detector (`[A-Z]{2}\d{6}` with context window).
- NZ phone detector (`+64`, `0x`, mobile prefixes `021/022/027`).
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
