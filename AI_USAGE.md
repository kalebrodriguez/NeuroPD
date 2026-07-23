# AI Usage Log

This file is an internal provenance and reproducibility record (spec Section 20).
AI assistance is permitted across this project. Recording it here does not make
any output reliable: all factual claims, citations, dataset details, statistics,
and results must be verified against real sources and executed code. Never
fabricate citations, quotations, dataset details, statistical results, or
conclusions.

## 2026-07-23

- Tool: Cursor agent (Opus 4.8)
- Task: Section 29 initial investigation — repository/environment inspection and
  live verification of OpenNeuro metadata for ds002778 and ds007526.
- Files: none created (read-only inspection and public metadata fetch).
- Verification: Repository state and environment facts obtained by executed shell
  commands. Dataset metadata obtained live from the OpenNeuro GraphQL API and the
  datasets' own `participants.tsv`/`README` (fetched files were only KB-scale
  metadata; no full datasets downloaded). Reported counts/sizes/licenses are from
  those executed queries, not assumptions.
- Owner review: Kaleb reviewed findings and approved cohort roles (ds007526 =
  development, ds002778 = external validation), public-repo status, environment
  plan (uv + Python 3.11), and the Milestone 0 scope.
- Corrections: None.

## 2026-07-23 (Milestone 0)

- Tool: Cursor agent (Opus 4.8)
- Task: Milestone 0 scaffolding — repository structure, uv/Python 3.11 environment,
  `pyproject.toml` + lockfile, data-safety `.gitignore`, provenance/logging/config
  modules, participant-isolation guardrail + tests, governance docs, and CI.
- Files: see the Milestone 0 commit history and PR (config, `src/neuropd/**`,
  `tests/**`, `configs/**`, docs, `.github/workflows/ci.yml`, tooling files).
- Verification: `uv sync`, `ruff check`, `ruff format --check`, `mypy`, and
  `pytest` executed locally; results recorded in the Milestone 0 report and
  `docs/research_log.md`. No datasets downloaded; no models trained.
- Owner review: pending PR review.
- Corrections: [to be filled in after review, or "None"].

## 2026-07-23 (Milestone 1)

- Tool: Cursor agent (Opus 4.8)
- Task: Dataset audit. Built a stdlib OpenNeuro metadata client and pure audit/region
  helpers; fetched metadata-only sidecars for both datasets; generated the audit
  report; verified the ds002778 eye condition against Jackson et al. 2019.
- Files: `src/neuropd/data/{openneuro,audit,regions}.py`,
  `scripts/{fetch_metadata,audit_datasets}.py`, `tests/{test_audit,test_regions}.py`,
  `docs/dataset_audit.md`, `docs/decisions/0004-*`, updated configs and docs.
- Verification: All numbers computed by executed code from real OpenNeuro metadata
  (participant counts, channels, sampling rates, durations, shared channels). Eye
  condition verified from the source publication's Methods (quoted). `ruff`, `mypy`,
  and `pytest` (22 passed, 7 skipped) executed. No full datasets downloaded; no models.
- Owner review: pending PR review.
- Corrections: None.
