# Changelog

All notable changes to this project will be documented in this file. Format roughly follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned

- HuggingFace `datasets` loader integration tests (currently the loader is implemented but untested).
- HTML compliance report.
- `docs/privacy-act-mapping.md` mapping each detector to specific Information Privacy Principles (IPPs 1–13) and Health Information Privacy Code 2020 references.

## [0.8.0] — 2026-06-22

### Added

- **Gemini LLM verification pass** — second-pass review of low-confidence findings using `gemini-2.5-flash` via `google-genai`. The verifier issues one JSON-mode classification call per finding (asking whether the value is genuinely the claimed PII type *in its surrounding context*), returns a `Verdict` of `confirmed` / `rejected` / `uncertain`, and `apply_verification()` re-scores the `ScanResult`: confirmed promotes confidence to `max(original, 0.95)`, rejected drops the finding, uncertain leaves it in place but annotated. Results are persisted in a SQLite cache at `data/llm_cache/cache.sqlite` so repeat audits do not re-burn quota. 429 / quota errors surface as `QuotaExceededError`; transient errors degrade to `uncertain` rather than aborting the run.

- **CLI flags** — `--verify-llm` and `--llm-threshold` (default 0.8) on the `scan` command. `.env` loading via `python-dotenv` is wired in lazily so the `[llm]` extra is only required when verification is requested.

- **`.env.example`** documenting `GOOGLE_API_KEY`. `.env`, `.env.bak`, and `data/llm_cache/` are gitignored.

### Changed

- `CellFinding` now carries the full cell value so the LLM verifier can use surrounding context. The new field defaults to `""` for backward compatibility.
- `[llm]` extra now includes `python-dotenv>=1.0` alongside `google-genai>=2.7.0`.

## [0.7.0] — 2026-06-22

### Added

- **Dataset-level Scanner** — `Scanner` class walks every object-dtype column of a DataFrame and applies each configured detector to each cell, producing a `ScanResult` with per-cell `CellFinding`s and aggregate counts by detector, severity, and column. Supports a custom detector subset and a `min_confidence` filter.

- **Loaders** — `nz_privacy_auditor.loaders.load(path)` dispatches on file extension to CSV / TSV / Parquet readers, returning a `pandas.DataFrame`. An optional HuggingFace `datasets` loader (`loaders.hf.load_hf`) is also provided behind the `[hf]` extra.

- **Report renderers** — `to_dict`, `to_json`, and `render_console` (Rich table) for `ScanResult`. JSON output includes both per-finding rows and summary statistics.

- **CLI** — `nz-privacy-auditor scan <path>` with `--format console|json`, `--output <file>`, `--detector <names>`, `--min-confidence`, and `--fail-on-finding` (exits 1 if any PII found, suitable for CI gating).

- **Te reo Māori name detector** — detects predominantly Māori given names and surnames from a curated gazetteer (~85 given names, ~60 surnames) with macron-aware fuzzy matching. Both the canonical form (`Tāne`, `Wikitōria`, `Te Heuheu`) and the macron-stripped form (`Tane`, `Wikitoria`) match the same entry. Confidence is 0.9 when the input preserved macrons (a signal of cultural care in data entry) and 0.7 otherwise. Multi-word names (`Te Heuheu`, `Te Aroha`, `Te Atatū`) are supported via longest-match alternation. Findings include a `kind` classification (`given`, `surname`, or `given_or_surname` when the same name appears in both lists). Severity is LOW because a personal name alone is not necessarily identifying under the Privacy Act 2020; the signal exists so auditors can apply additional IPP 4 and IPP 8 care to records containing culturally significant te reo Māori identifiers.

- **NZ address detector** — flags values that look like NZ street addresses by combining three signals: (1) street-suffix shape (number + 1–4 words + recognised suffix such as `Street`, `Road`, `Avenue`, `Drive`, `Quay`, plus abbreviations `St`, `Rd`, `Ave`, `Tce`, etc., with optional unit prefix like `5/123` and unit letters like `12A`); (2) NZ 4-digit postcode anywhere in the value; (3) NZ region / city / suburb gazetteer (16 regions, ~25 major cities/towns, ~40 common metropolitan suburbs in Auckland, Wellington, and Christchurch). Signals from inside the address span itself are excluded. Confidence scales from 0.5 (shape only) to 0.7 (shape + one signal) to 0.9 (shape + postcode + location). Severity is MEDIUM as quasi-identifier under the Privacy Act 2020.

- **NZ phone detector** — recognises NZ phone numbers in international (`+64`, `0064`) and national (`0` trunk) formats with permissive separators (spaces, hyphens, dots, parentheses). The detector strips separators and prefixes, then validates the National Significant Number against the New Zealand Numbering Plan: mobile (`2X`, NSN 8–10 digits), geographic landline (areas 3, 4, 6, 7, 9; NSN 8 digits), toll-free (`0800`, `0508`; NSN 9–10 digits), and premium-rate (`0900`; NSN 8–9 digits). Findings carry the canonical E.164 form and the phone-kind label. Confidence is 1.0 with an explicit country code and 0.8 for national-form matches. Severity is MEDIUM (quasi-identifier under the Privacy Act 2020). Exposes a `to_e164()` helper for downstream normalisation.

- **Driver licence detector** — recognises NZ Waka Kotahi | NZ Transport Agency driver licence numbers in the format `[A-Z]{2}\d{6}` (e.g. `BQ739482`). NZTA does not publish a check-digit algorithm, so the detector applies a 300-character keyword-proximity heuristic (matching the Microsoft Purview NZ DLP rule): findings near keywords *licence*, *license*, *driver*, *DL* (uppercase), *NZTA*, or *Waka Kotahi* receive confidence 0.9; bare pattern matches receive confidence 0.5. 12 tests covering keyword variants, proximity boundary, case sensitivity, and shape rejection.

- **NHI (National Health Index) detector** — recognises both the legacy `AAANNNC` (mod-11 numeric check digit) and new `AAANNAX` (mod-23 alphabetic check digit) formats per HISO 10046:2024. Uses the 24-letter NHI alphabet (A–Z excluding I and O) with weights `(7, 6, 5, 4, 3, 2)`. Only checksum-validated matches are emitted. Test vectors drawn from Health NZ \| Te Whatu Ora's published format-change examples (`ZAA0067`, `ZAA0075`, `ZAA0083` for legacy; `ACA31FM`, `ASE37QK`, `ARE62RS` for new). Case-insensitive matching with normalised uppercase in the finding context.

### Planned

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

[Unreleased]: https://github.com/ShahnawazKakarh/nz-privacy-auditor/compare/v0.8.0...HEAD
[0.8.0]: https://github.com/ShahnawazKakarh/nz-privacy-auditor/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/ShahnawazKakarh/nz-privacy-auditor/compare/v0.1.0...v0.7.0
[0.1.0]: https://github.com/ShahnawazKakarh/nz-privacy-auditor/releases/tag/v0.1.0
