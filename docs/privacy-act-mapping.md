# Privacy Act 2020 mapping

This document maps each detector in `nz-privacy-auditor` to the relevant Information Privacy Principles (IPPs) of the [Privacy Act 2020](https://www.legislation.govt.nz/act/public/2020/0031/latest/LMS23223.html) and, where applicable, to clauses of the [Health Information Privacy Code 2020](https://www.privacy.org.nz/publications/codes-of-practice/health-information-privacy-code-2020-and-related-material/) (HIPC). It is intended as a reference for auditors, privacy officers, and ML practitioners using the tool to satisfy compliance obligations.

> **Not legal advice.** This mapping reflects the authors' good-faith reading of the statute and Code. For binding interpretation consult the [Office of the Privacy Commissioner](https://www.privacy.org.nz/) and a qualified legal professional.

## The Information Privacy Principles at a glance

| # | Principle | One-line summary |
|---|---|---|
| IPP 1  | Purpose of collection         | Only collect personal information for a lawful purpose connected with your function. |
| IPP 2  | Source                        | Collect personal information directly from the individual where possible. |
| IPP 3  | Awareness                     | Make individuals aware of the collection and its purpose. |
| IPP 4  | Manner of collection          | Do not collect by unlawful, unfair, or unreasonably intrusive means. |
| IPP 5  | Storage and security          | Protect personal information against loss, unauthorised access, use, modification, or disclosure. |
| IPP 6  | Access                        | Individuals have the right to access their personal information. |
| IPP 7  | Correction                    | Individuals have the right to request correction. |
| IPP 8  | Accuracy                      | Check accuracy before using or disclosing personal information. |
| IPP 9  | Retention                     | Do not keep personal information longer than necessary. |
| IPP 10 | Use                           | Use personal information only for the purpose it was collected. |
| IPP 11 | Disclosure                    | Limits on disclosure, including to third parties. |
| IPP 12 | Cross-border disclosure       | Special rules for disclosure outside New Zealand. |
| IPP 13 | Unique identifiers            | Restrictions on assigning, using, and requiring unique identifiers. |

## Detector-by-detector mapping

### IRD number — `ird` detector

| IPP | Why this detector matters |
|---|---|
| **IPP 13** (unique identifiers) | An IRD number is a regulated unique identifier issued by Inland Revenue. Training an ML model on raw IRDs, or republishing a dataset containing them, is generally inconsistent with IPP 13's requirement to assign unique identifiers only where necessary for the agency's functions and to take reasonable steps to minimise misuse. |
| IPP 5 (security)     | Unredacted IRDs in training data are a security-incident waiting to happen. The detector lets you confirm they are absent before storage / sharing. |
| IPP 10 (use)         | If IRD numbers were collected for tax purposes and end up in a marketing ML pipeline, IPP 10 is engaged. |
| IPP 11 (disclosure)  | Publishing a model checkpoint trained on raw IRDs, even after fine-tuning, is potentially a disclosure under IPP 11. |

**Authority for the checksum:** Inland Revenue, *Algorithm for IRD numbers* (publicly available specification, primary + secondary mod-11 weight tables).

### NHI number — `nhi` detector

| IPP / HIPC Rule | Why this detector matters |
|---|---|
| **HIPC Rule 12 / IPP 13** (unique identifiers, health) | The NHI is the unique identifier for an individual receiving health services in New Zealand, governed by HIPC Rule 12. Use, disclosure, and storage of NHIs has stricter constraints than generic IPPs. |
| HIPC Rule 5 (security)   | Health information is sensitive personal information. Unredacted NHIs in research / ML datasets are a serious breach risk. |
| HIPC Rule 11 (disclosure) | Disclosure of NHIs to anyone outside the original treating agency requires lawful basis (usually consent or a specific authority). |
| HIPC Rule 8 (accuracy)   | Both NHI formats (legacy AAANNNC, new AAANNAX) have published checksums. Records that fail the checksum are likely transcription errors and engage Rule 8. |

**Authority for the checksums:** Health NZ \| Te Whatu Ora, HISO 10046:2024 (NHI specification), [upcoming-changes-nhi page](https://www.tewhatuora.govt.nz/health-services-and-programmes/health-identity/national-health-index/upcoming-changes-nhi).

### Driver licence number — `driver_licence` detector

| IPP | Why this detector matters |
|---|---|
| **IPP 13** (unique identifiers) | The driver licence number is a unique identifier issued by Waka Kotahi \| NZ Transport Agency. |
| IPP 5 (security)    | Driver licence numbers are routinely targeted in identity-fraud schemes; they should be redacted from training data and from any externally-shared artefacts. |
| IPP 11 (disclosure) | Publishing datasets containing licence numbers is generally a disclosure event. |

NZTA does **not** publish a check-digit algorithm; this detector relies on regex shape + 300-character keyword proximity (the same approach as the [Microsoft Purview NZ DLP rule](https://learn.microsoft.com/en-us/purview/sit-defn-new-zealand-driver-licence-number)). The optional `--verify-llm` second-pass is particularly valuable for this detector because the shape `[A-Z]{2}\d{6}` overlaps heavily with SKUs, flight codes, and order references.

### NZ phone number — `phone` detector

| IPP | Why this detector matters |
|---|---|
| **IPP 1, 3** (purpose, awareness) | Phone numbers collected for contact must not silently flow into ML training corpora without addressing the original purpose of collection. |
| IPP 5 (security)    | Quasi-identifier alone; combined with name + address, sufficient for re-identification. |
| IPP 11 (disclosure) | Publishing user-generated content datasets containing NZ phone numbers (forum threads, chat logs) typically requires removing or redacting them first. |

### NZ address — `address` detector

| IPP | Why this detector matters |
|---|---|
| **IPP 5** (security)        | Addresses are sensitive personal information (residential addresses especially) and are required to be kept secure. |
| IPP 11 (disclosure)         | Disclosure of residential addresses to third parties is a frequent vector of harm (stalking, domestic-violence cases, dox attacks). The detector lets you flag and remove these before any external release. |
| IPP 4 (manner of collection) | If addresses were inferred from IP geolocation rather than collected directly, IPP 4 (fairness, intrusiveness) may be engaged. |

### Te reo Māori names — `maori_name` detector

| IPP | Why this detector matters |
|---|---|
| **IPP 4** (manner of collection) | Personal names are personal information. Names of Māori individuals carry cultural significance — collection and use should be conducted with appropriate cultural care. |
| **IPP 8** (accuracy)             | Macron preservation is a basic accuracy requirement. A te reo name with stripped macrons is, strictly, inaccurate personal information; IPP 8 obliges checks before use or disclosure. |
| Tikanga / Mātauranga Māori (informal) | Beyond statute, the [Te Mana Raraunga charter](https://www.temanararaunga.maori.nz/) and emerging Māori Data Sovereignty principles place additional kaitiaki obligations on data containing Māori personal information. |

The detector emits at LOW severity precisely because a personal name alone is not necessarily identifying; the flag is intended to *signal* records that warrant additional IPP 4 / IPP 8 care, not to claim each match is unlawful PII.

## When `--verify-llm` is used

The LLM verification pass sends each low-confidence finding to Google's Gemini API. This is a cross-border disclosure of personal information for the duration of the verification request, and is **subject to IPP 12** (cross-border disclosure).

> **IPP 12 reminder:** Personal information may be disclosed to a foreign person or entity only if the recipient is subject to comparable privacy protections (e.g. via contractual safeguards) or one of the IPP 12 exceptions applies.

In practice this means:

1. **Auditing your own data** under your own authority is generally fine — you are the holder and you are verifying the data, not disclosing it to a third party for their own use.
2. **Auditing a dataset on behalf of another agency** before delivery may require an information-sharing agreement that explicitly contemplates LLM-based verification.
3. **Sensitive datasets** (health records under HIPC, criminal-justice data) generally warrant running the auditor *without* `--verify-llm` and relying on the checksum-validated detectors alone, or running a local LLM behind your firewall.

The disk cache (`data/llm_cache/cache.sqlite`) keeps verified findings locally so the same value is not re-sent to Gemini on every run.

## Beyond the Privacy Act

This tool focuses on the Privacy Act 2020 and the Health Information Privacy Code 2020. Adjacent regimes that may also apply to NZ ML datasets:

- **Te Tiriti o Waitangi / Treaty of Waitangi** — partnership, protection, and participation obligations toward Māori in data collection and use.
- **Māori Data Sovereignty** ([Te Mana Raraunga](https://www.temanararaunga.maori.nz/)) — kaitiakitanga over data about Māori.
- **Algorithm Charter for Aotearoa New Zealand** — government-agency obligations for algorithmic decision systems.
- **OECD Privacy Guidelines / APEC Cross-Border Privacy Rules** — for international data flows.

## Updating this document

If you spot an error or a missing principle / rule, please [open an issue](https://github.com/ShahnawazKakarh/nz-privacy-auditor/issues) or a PR. Statutory references should always cite the [legislation.govt.nz](https://www.legislation.govt.nz/) canonical text.
