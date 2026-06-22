# nz-privacy-auditor

[![CI](https://github.com/ShahnawazKakarh/nz-privacy-auditor/actions/workflows/ci.yml/badge.svg)](https://github.com/ShahnawazKakarh/nz-privacy-auditor/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests](https://img.shields.io/badge/tests-161%20passing-brightgreen.svg)](#testing)
[![Privacy Act 2020](https://img.shields.io/badge/Privacy%20Act-2020-blue.svg)](https://www.legislation.govt.nz/act/public/2020/0031/latest/LMS23223.html)

> **Privacy Act 2020 compliance auditor for ML datasets.** Scans CSV, Parquet, and HuggingFace datasets and flags New-Zealand-specific personal information — IRD numbers, NHI numbers, driver licence numbers, NZ phone and address patterns, and te reo Māori personal names — using a hybrid **regex + checksum + gazetteer + LLM verification** pipeline.

---

## Why this exists

The [Privacy Act 2020](https://www.legislation.govt.nz/act/public/2020/0031/latest/LMS23223.html) governs the collection, use, and disclosure of personal information in Aotearoa New Zealand. ML practitioners working with NZ data — health records, government datasets, customer corpora — need to verify that training data is free of regulated identifiers **before** models are fine-tuned, shared, or shipped.

Generic PII tools ([Microsoft Presidio](https://github.com/microsoft/presidio), [scrubadub](https://github.com/LeapBeyond/scrubadub), [DLP dictionaries](https://help.zscaler.com/zia/understanding-predefined-dlp-dictionaries)) catch global formats (US SSN, EU phone, generic credit card) but miss the NZ-specific identifiers that matter most under the Privacy Act and the [Health Information Privacy Code 2020](https://www.privacy.org.nz/publications/codes-of-practice/health-information-privacy-code-2020-and-related-material/):

| NZ identifier | Why generic tools miss it |
|---|---|
| **IRD number** | NZ-specific mod-11 checksum with primary + secondary weight tables (Inland Revenue spec) |
| **NHI number** | Two coexisting formats — legacy AAANNNC (mod 11) and new AAANNAX (mod 23) per HISO 10046:2024 — over a 24-letter alphabet that omits I and O |
| **NZ driver licence** | `[A-Z]{2}\d{6}` shape is indistinguishable from SKUs / flight refs without contextual disambiguation |
| **NZ phone** | NSN length rules vary per kind (mobile 02X, landlines 03/04/06/07/09, toll-free 0800/0508, premium 0900) |
| **NZ address** | NZ Post 4-digit postcodes, NZ-specific suburbs / regions, te reo place names with macrons |
| **Te reo Māori names** | Macron-stripping and IPP 4 / IPP 8 considerations for culturally significant data |

`nz-privacy-auditor` fills that gap, with **checksum-validated detection** (no false positives where a checksum exists), a **300-character keyword-proximity heuristic** (matching Microsoft Purview's NZ DLP rule) for identifiers without published checksums, and an optional **Gemini 2.5 Flash second-pass** that catches the residual ambiguous cases.

## Status

✅ **v0.8.0** — production-ready. All six detectors, CSV/Parquet/HuggingFace loaders, a dataset-level Scanner, a Click CLI, JSON / Rich-console reports, and the Gemini LLM verification pass are implemented and tested (161 passing tests, CI green on Python 3.11 and 3.12).

## What it detects

| Detector | Approach | Severity | Confidence policy | Since |
|---|---|---|---|---|
| **IRD number** | regex + Inland Revenue mod-11 (primary + secondary weights), range 10M–150M | HIGH | 1.0 (checksum-valid only) | v0.1.0 |
| **NHI number** | regex + Health NZ mod-11 (legacy) and mod-23 (new format) per HISO 10046:2024 | HIGH | 1.0 (checksum-valid only) | v0.2.0 |
| **Driver licence** | regex `[A-Z]{2}\d{6}` + 300-char keyword proximity | HIGH | 0.9 with keyword (*licence*, *DL*, *NZTA*, …), 0.5 otherwise | v0.3.0 |
| **NZ phone** | regex + NSN validation against the NZ Numbering Plan, normalises to E.164 | MEDIUM | 1.0 with `+64`, 0.8 national-form | v0.4.0 |
| **NZ address** | street-suffix shape + 4-digit postcode + 16 regions / 65+ city & suburb gazetteer | MEDIUM | 0.5 / 0.7 / 0.9 by supporting signals | v0.5.0 |
| **Te reo Māori names** | macron-aware curated gazetteer (~85 given, ~60 surname); multi-word names supported | LOW | 0.9 macron-preserved, 0.7 stripped | v0.6.0 |
| **LLM verification** | Gemini 2.5 Flash second-pass over findings below `--llm-threshold` (default 0.8); SQLite-cached | — | promotes to ≥0.95 on confirm, drops on reject | v0.8.0 |

## Install

```bash
pip install -e ".[dev]"            # development install
pip install -e ".[llm]"            # add Gemini second-pass support
pip install -e ".[hf]"             # add HuggingFace `datasets` loader
pip install -e ".[all]"            # everything
```

Requires Python 3.10+. Tested on macOS and Linux; CI runs on Ubuntu (3.11, 3.12).

## Quick start

### CLI

```bash
nz-privacy-auditor scan path/to/data.csv
nz-privacy-auditor scan path/to/data.parquet --format json --output report.json
nz-privacy-auditor scan data.csv --detector ird,nhi --min-confidence 0.7
nz-privacy-auditor scan data.csv --fail-on-finding          # exit 1 if any PII; CI gate
nz-privacy-auditor scan data.csv --verify-llm               # second-pass review with Gemini
```

### A real worked example

A small dataset with one genuine NZ identifier and one easy false positive:

```csv
id,note
1,IRD 49091850 on file
2,Reference BQ739482 in our SKU catalog
```

**Without LLM verification** — the driver-licence detector flags the SKU code because it matches `[A-Z]{2}\d{6}`:

```
nz-privacy-auditor scanned 2 rows across 1 string columns
Total findings: 2  •  Detectors: ird, nhi, driver_licence, phone, address, maori_name
By severity: high 2
By detector: driver_licence 1, ird 1
                             Findings
┏━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ row ┃ column ┃ detector       ┃ severity ┃ confidence ┃ value    ┃
┡━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━┩
│   0 │ note   │ ird            │ high     │       1.00 │ 49091850 │
│   1 │ note   │ driver_licence │ high     │       0.50 │ BQ739482 │
└─────┴────────┴────────────────┴──────────┴────────────┴──────────┘
```

**With `--verify-llm`** — Gemini reads the surrounding context, recognises "SKU catalog", and rejects the false positive. Only the genuine IRD remains:

```
nz-privacy-auditor scanned 2 rows across 1 string columns
Total findings: 1  •  Detectors: ird, nhi, driver_licence, phone, address, maori_name
By severity: high 1
By detector: ird 1
                          Findings
┏━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ row ┃ column ┃ detector ┃ severity ┃ confidence ┃ value    ┃
┡━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━┩
│   0 │ note   │ ird      │ high     │       1.00 │ 49091850 │
└─────┴────────┴──────────┴──────────┴────────────┴──────────┘
```

This is the principal value of the hybrid pipeline: **regex + checksum catches the things that have published structure, and the LLM catches the things that don't.** The verifier only runs on findings whose initial confidence is below `--llm-threshold` (default 0.8) — high-confidence checksum-validated findings never burn quota.

### Python

```python
import pandas as pd
from nz_privacy_auditor import Scanner

df = pd.read_csv("patients.csv")
result = Scanner().scan_dataframe(df)

print(f"{result.total_findings} findings across {len(result.columns_scanned)} columns")
for cf in result.findings:
    print(cf.row, cf.column, cf.finding.detector, cf.finding.value, cf.finding.confidence)
```

With LLM verification programmatically:

```python
from dotenv import load_dotenv
from nz_privacy_auditor import Scanner, apply_verification
from nz_privacy_auditor.verifiers import GeminiVerifier

load_dotenv()                                # picks up GOOGLE_API_KEY from .env
result = Scanner().scan_dataframe(df)
verifier = GeminiVerifier()                  # cache at data/llm_cache/cache.sqlite
verified = apply_verification(result, verifier, threshold=0.8)
verifier.close()
```

A single detector in isolation:

```python
from nz_privacy_auditor.detectors import IRDDetector

for finding in IRDDetector().scan("Please reference IRD 49-091-850 on the form."):
    print(finding)
# Finding(detector='ird', severity=<Severity.HIGH: 'high'>, value='49-091-850',
#         start=17, end=27, confidence=1.0, context={'normalised': '49091850'})
```

## Pipeline

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Loader     │ → │ Detectors    │ → │ LLM verify   │ → │ Report       │
│ csv/parquet/ │   │ (regex +     │   │ (Gemini 2.5  │   │ JSON / Rich  │
│ hf datasets  │   │  checksum +  │   │  Flash, SQL  │   │ table / CI   │
│              │   │  gazetteer)  │   │  cache)      │   │ exit code    │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
                          │                  ▲
                          └── ScanResult ────┤
                              (per-cell      │ only confidence < threshold
                               findings +    │
                               counts)       │
```

## How the checksums work

### IRD (Inland Revenue)

NZ IRD numbers are 8 or 9 digits with a mod-11 check digit. Inland Revenue publishes the algorithm: a **primary** weight set is applied first, and if it yields a check digit of 10, a **secondary** weight set is used instead. IRDs below 10,000,000 are not issued; the upper sanity bound is 150,000,000.

```
primary weights:    (3, 2, 7, 6, 5, 4, 3, 2)
secondary weights:  (7, 4, 3, 2, 5, 2, 7, 6)
```

The detector emits findings **only** for checksum-validated matches — eliminating false positives that pure regex tools produce on columns containing zip codes, phone numbers, or order IDs.

### NHI (National Health Index)

NHI uses a 24-letter alphabet (A–Z excluding I and O, mapped 1–24) with weights `(7, 6, 5, 4, 3, 2)` over the first six characters:

- **Legacy AAANNNC** (3 letters + 3 digits + 1 numeric check digit): mod 11. Per HISO spec, a remainder of zero produces no valid check digit and the NHI is invalid.
- **New AAANNAX** (3 letters + 2 digits + 1 letter + 1 letter check digit): mod 23 (changed from mod 24 to reduce single-character substitution errors from ~7% to ~0.2%, per [Health NZ](https://www.tewhatuora.govt.nz/health-services-and-programmes/health-identity/national-health-index/upcoming-changes-nhi)).

## CLI reference

```
Usage: nz-privacy-auditor scan [OPTIONS] PATH

  Scan a dataset for Privacy Act 2020 PII issues.

Options:
  --format [console|json]    Output format.  [default: console]
  -o, --output PATH          Write output to a file (JSON only).
  --detector TEXT            Comma-separated detector names. Default: all.
                             Choices: ird, nhi, driver_licence, phone, address, maori_name
  --min-confidence FLOAT     Drop findings below this confidence.  [default: 0.0]
  --fail-on-finding          Exit 1 if any findings (useful in CI).
  --verify-llm               Run Gemini second-pass on low-confidence findings.
  --llm-threshold FLOAT      Only verify findings below this confidence.  [default: 0.8]
  -h, --help                 Show this message and exit.
```

## Privacy Act 2020 mapping

Each detector maps to one or more Information Privacy Principles (IPPs 1–13) under the Privacy Act 2020 and, where relevant, to clauses of the Health Information Privacy Code 2020. See [`docs/privacy-act-mapping.md`](docs/privacy-act-mapping.md) for the full mapping.

## Comparison

| | nz-privacy-auditor | Presidio | scrubadub | Microsoft Purview NZ |
|---|---|---|---|---|
| NZ IRD with mod-11 checksum | ✅ | ❌ | ❌ | regex only |
| NZ NHI legacy + new format | ✅ | ❌ | ❌ | regex only |
| NZ driver licence + keyword proximity | ✅ | ❌ | ❌ | ✅ |
| NZ phone NSN validation | ✅ | ❌ | partial | partial |
| NZ address (postcode + gazetteer) | ✅ | ❌ | ❌ | ❌ |
| Te reo Māori names (macron-aware) | ✅ | ❌ | ❌ | ❌ |
| LLM verification (cached) | ✅ | ❌ | ❌ | ❌ |
| CLI + dataset-level report | ✅ | partial | ❌ | enterprise UI |
| Open source | MIT | MIT | Apache-2.0 | proprietary |

## Development

```bash
git clone https://github.com/ShahnawazKakarh/nz-privacy-auditor.git
cd nz-privacy-auditor
pyenv local 3.11.1
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,llm,hf]"
pre-commit install

pytest                              # 161 tests
ruff check src tests
ruff format src tests
```

For the LLM tests, the Gemini client is mocked end-to-end — no real API calls are made in CI. To exercise the real pipeline locally, copy `.env.example` to `.env` and set `GOOGLE_API_KEY`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the process for adding a new detector.

## Citation

If you use this tool in research, please cite it. Once a Zenodo DOI is minted it will appear here; in the meantime, BibTeX:

```bibtex
@software{khan2026nzprivacyauditor,
  author       = {Khan, Muhammad Shahnawaz},
  title        = {nz-privacy-auditor: Privacy Act 2020 compliance auditor for ML datasets},
  year         = {2026},
  version      = {0.8.0},
  url          = {https://github.com/ShahnawazKakarh/nz-privacy-auditor},
  orcid        = {0009-0007-4055-6563}
}
```

See [`CITATION.cff`](CITATION.cff) for the machine-readable citation file. GitHub renders a "Cite this repository" widget from it automatically.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This tool helps identify potential Privacy Act 2020 issues but does **not** constitute legal advice, a Privacy Impact Assessment, or a substitute for review by a qualified privacy professional. Always consult the [Office of the Privacy Commissioner](https://www.privacy.org.nz/) and your organisation's privacy officer for compliance decisions on production systems.

The bundled NZ location gazetteer is a compact representative sample, not an authoritative postcode database; for production-grade address validation, augment with the [NZ Post postcode dataset](https://www.nzpost.co.nz/business/sending-within-nz/postcodes).
