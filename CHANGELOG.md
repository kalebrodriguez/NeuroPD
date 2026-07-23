# Changelog

All notable changes to NeuroPD are documented here. The format is loosely based
on [Keep a Changelog](https://keepachangelog.com/), and the project follows
milestone-based development (spec Section 22).

## [Unreleased]

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
