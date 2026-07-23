# Changelog

All notable changes to NeuroPD are documented here. The format is loosely based
on [Keep a Changelog](https://keepachangelog.com/), and the project follows
milestone-based development (spec Section 22).

## [Unreleased]

### Added (Milestone 1 — dataset audit)
- Reproducible, stdlib-only OpenNeuro **metadata client** (`neuropd.data.openneuro`)
  that traverses snapshot trees and downloads only small `*.json`/`*.tsv` sidecars
  (binary recordings are refused; runs are resumable).
- Pure audit and scalp-region helpers (`neuropd.data.audit`, `neuropd.data.regions`)
  with offline unit tests.
- Scripts `fetch_metadata.py` and `audit_datasets.py`; generated
  `docs/dataset_audit.md` and `data/metadata/audit_summary.json` from real metadata.
- Verified dataset facts written into `configs/data/*.yaml`; decision records for the
  eye-condition verification (ADR 0002 outcome) and the ds002778 line-frequency/notch
  handling (ADR 0004).

### Verified findings (Milestone 1)
- Both cohorts are **eyes-open** resting (no eye-condition mismatch).
- **31 shared 10-20 scalp channels** across the two montages (all 5 regions covered).
- Cross-dataset differences documented: sampling rate (512 vs 250 Hz), class imbalance
  (ds007526 ~4:1 PD:HC), age/sex confound in the development cohort, and a ds002778
  line-frequency metadata error (9/46 recordings).

### Added (Milestone 0 — repository and environment)
- Project scaffolding following the specified repository structure.
- `uv`-managed environment pinned to Python 3.11 with `pyproject.toml`,
  `uv.lock`, and `.python-version`.
- Core infrastructure modules: `config`, `logging`, `provenance`, and a `neuropd`
  CLI with a `provenance` command.
- Participant-isolation guardrail (`neuropd.data.splits`) with unit tests — the
  project's primary scientific safeguard.
- Data-safety `.gitignore` (raw/derived data, secrets, and environment files are
  never committed) and `.env.example`.
- Governance and documentation: `README`, `LICENSE`, `CITATION.cff`, `AI_USAGE.md`,
  `CONTRIBUTING.md`, `docs/research_log.md`, initial decision records, and
  neuroscience/limitations doc stubs.
- Tooling: `Makefile`, ruff/mypy configuration, pytest suite, and GitHub Actions
  CI that runs lint/typecheck/tests without downloading datasets.
- Verified, versioned dataset configuration for ds002778 and ds007526 (audited
  metadata only; scientific parameters flagged for Milestone 1 verification).
