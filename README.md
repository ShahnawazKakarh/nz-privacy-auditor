# nz-privacy-auditor

[![CI](https://github.com/ShahnawazKakarh/nz-privacy-auditor/actions/workflows/ci.yml/badge.svg)](https://github.com/ShahnawazKakarh/nz-privacy-auditor/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **Privacy Act 2020 compliance auditor for ML datasets.** Scans CSV, Parquet, and HuggingFace datasets and flags New-Zealand-specific personal information — IRD numbers, NHI numbers, driver licence numbers, NZ phone and address patterns, and te reo Māori personal names — using a hybrid **regex + checksum + NER + LLM verification** pipeline.

---

## Why

The [Privacy Act 2020](https://www.legislation.govt.nz/act/public/2020/0031/latest/LMS23223.html) governs the collection, use, and disclosure of personal information in Aotearoa New Zealand. ML practitioners working with NZ data — health records, government datasets, customer corpora — need a way to verify that training corpora are free of regulated identifiers before models are fine-tuned, shared, or shipped.

Generic PII tools (Presidio, scrubadub, etc.) catch global formats (US SSN, EU phone) but miss NZ-specific identifiers:

- **IRD numbers** (Inland Revenue tax IDs, mod-11 checksum)
- **NHI numbers** (National Health Index, 3 letters + 4 digits legacy / 3+3+1 new format, mod-11 checksum)
- **NZ driver licence numbers** (2 letters + 6 digits)
- **NZ phone formats** (`+64`, `0x`, `021/022/027` mobile prefixes)
- **NZ addresses** (street suffixes + suburb / region gazetteer)
- **Te reo Māori names** (macron-aware NER, frequently misclassified by English-trained models)

`nz-privacy-auditor` fills that gap.

## Status

🚧 **Alpha (v0.1.0)** — IRD detector with mod-11 validation is implemented and tested. NHI, driver licence, phone, address, and te reo name detectors are on the roadmap below.

## Install

```bash
pip install -e ".[dev]"            # development install
pip install -e ".[ner,llm,hf]"     # with optional NER, LLM verification, HuggingFace datasets
```

Requires Python 3.10+.

## Quick usage

```python
from nz_privacy_auditor.detectors import IRDDetector

detector = IRDDetector()
for finding in detector.scan("Please reference IRD 49-091-850 on the form."):
    print(finding)
# Finding(detector='ird', severity=<Severity.HIGH: 'high'>, value='49-091-850',
#         start=17, end=27, confidence=1.0, context={'normalised': '49091850'})
```

A dataset-level scanner CLI (`nz-privacy-auditor scan path/to/data.csv`) lands once the detector suite is complete.

## Detector roadmap

| Detector            | Approach                                | Severity | Status        |
|---------------------|-----------------------------------------|----------|---------------|
| IRD number          | regex + IR mod-11 (primary + secondary) | HIGH     | ✅ v0.1.0      |
| NHI number          | regex + Health NZ mod-11 / mod-23        | HIGH     | ✅ v0.2.0      |
| Driver licence      | regex `[A-Z]{2}\d{6}` + keyword proximity | HIGH     | ✅ v0.3.0      |
| NZ phone            | `+64` / `0x` patterns, mobile prefixes  | MEDIUM   | ⏳ planned     |
| NZ address          | suffix + suburb / region gazetteer      | MEDIUM   | ⏳ planned     |
| Te reo Māori names  | macron-aware NER + name list            | LOW      | ⏳ planned     |
| LLM verification    | Gemini second-pass for ambiguous spans  | —        | ⏳ planned     |

## Pipeline (planned)

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Loader     │ →  │ Regex pass   │ →  │ NER pass     │ →  │ LLM verify   │
│ csv/parquet/ │    │ + checksums  │    │ (spaCy /     │    │ (Gemini      │
│ HF datasets  │    │              │    │  transformer)│    │  2.5 Flash)  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                            │                   │                   │
                            └───────────────────┴───────────────────┘
                                                ↓
                                       ┌──────────────────┐
                                       │ Compliance report│
                                       │ (JSON + HTML)    │
                                       └──────────────────┘
```

## Development

```bash
pyenv local 3.11.1
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest                              # run tests
ruff check --fix src tests          # lint
ruff format src tests               # format
pre-commit install                  # optional: install git hooks
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development workflow and the process for adding a new detector.

## How IRD validation works

NZ IRD numbers are 8 or 9 digits with a mod-11 check digit. Inland Revenue publishes the algorithm: a **primary** weight set is applied first, and if it yields a check digit of 10, a **secondary** weight set is used instead. We also enforce a range bound (10,000,000 – 150,000,000) since IRDs below 10M are not issued.

```
primary weights:    (3, 2, 7, 6, 5, 4, 3, 2)
secondary weights:  (7, 4, 3, 2, 5, 2, 7, 6)
```

The detector emits findings **only** for checksum-validated matches — eliminating the false positives that pure regex tools produce on dataset columns containing zip codes, phone numbers, or order IDs.

## Citing

If you use this tool, please cite via [`CITATION.cff`](CITATION.cff).

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This tool helps identify potential Privacy Act 2020 issues but does **not** constitute legal advice or a substitute for a Privacy Impact Assessment. Always consult the [Office of the Privacy Commissioner](https://www.privacy.org.nz/) and your organisation's privacy officer for compliance decisions.
