# Contributing

Thanks for your interest in improving `nz-privacy-auditor`. Contributions are welcome — new detectors, additional NZ identifier formats, gazetteer expansion, or improvements to the LLM verification layer are all useful.

## Development setup

```bash
git clone https://github.com/ShahnawazKakarh/nz-privacy-auditor.git
cd nz-privacy-auditor
pyenv local 3.11.1            # or any Python >= 3.10
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install            # optional but recommended
```

Verify:

```bash
pytest
ruff check src tests
```

## Adding a new detector

1. Create `src/nz_privacy_auditor/detectors/<name>.py` exposing a class that subclasses `Detector` and implements `scan(value: str) -> Iterable[Finding]`.
2. Set the `name` and `severity` class attributes.
3. If the identifier has a published checksum (mod-11, Luhn, etc.), implement it as a private helper in the same module and validate it before emitting a finding. **Only emit checksum-validated matches.**
4. Register the detector in `src/nz_privacy_auditor/detectors/__init__.py`.
5. Add tests in `tests/test_<name>.py` covering:
   - At least three known-valid identifiers (from official spec or worked examples)
   - At least three checksum-invalid identifiers
   - Edge cases: wrong length, non-numeric input, out-of-range
   - Detection behaviour: plain, hyphenated / spaced, multiple matches, offset correctness
6. Update the roadmap table in `README.md`.
7. Add an entry to `CHANGELOG.md` under the `[Unreleased]` section.

## Adding a new loader

1. Add `src/nz_privacy_auditor/loaders/<format>.py` exposing `load(path) -> pandas.DataFrame`.
2. Register in the loader factory.
3. Add a test fixture under `tests/fixtures/` and a smoke test.

## Code style

- Ruff is the single source of truth for lint + formatting (configured in `pyproject.toml`). Run `ruff format` and `ruff check --fix` before committing.
- Type hints required on public functions.
- Detectors must be stateless and thread-safe — a single instance is reused across rows.

## Commit messages

Conventional commits, e.g.

- `feat: add NHI detector with mod-11 validation`
- `fix: handle empty value in IRD scanner`
- `docs: clarify checksum-only emission policy`
- `test: add edge cases for te reo name detector`

## Reporting issues

Include Python version, OS, the command you ran, and a minimal reproducer. For false-positive or false-negative reports, include the exact input string and which detector misfired.

## License

By contributing you agree that your contributions are licensed under the MIT License of this project.
