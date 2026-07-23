# AGENTS.md

Guidance for coding agents working in the NeuroPD repository. The controlling
specification is the NeuroPD Master Specification provided by the project owner;
this file summarizes operational essentials. When in doubt, follow the spec and
ask the owner before changing the scientific design.

## What this project is

A reproducible, research-grade pipeline investigating whether interpretable
resting-state EEG biomarkers for Parkinson's disease generalize **across
independent datasets**. It is a **research tool, not a medical device**, and must
never be described as diagnosing Parkinson's disease.

## Environment & common commands

- Environment manager: **`uv`**; Python is pinned to **3.11** via `.python-version`.
- Install `uv` if missing: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  (then ensure `~/.local/bin` is on `PATH`).

```bash
make install     # uv sync --extra dev   (creates .venv, installs deps + dev tools)
make lint        # uv run ruff check .
make format      # uv run ruff format .
make typecheck   # uv run mypy
make test        # uv run pytest
make check       # lint + typecheck + test
make smoke       # fast smoke + participant-isolation tests
uv run neuropd --help
```

First-time setup downloads the interpreter and dependencies (MNE, scikit-learn,
Streamlit, etc.); allow a few minutes. CI runs the same lint/typecheck/test steps
and **must not download full EEG datasets**.

## Hard rules (do not violate)

- **Never commit data or secrets.** Raw/derived EEG, `.env`, and any identifiable
  or controlled data must never be committed. `.gitignore` enforces this — do not
  weaken it. Raw data live under `data/raw/` and are immutable.
- **Participant isolation is sacred.** All recordings/sessions from one participant
  stay in one split. Keep `tests/test_splits.py` green.
- **No fabricated results/citations.** Every number comes from executed code; every
  citation is verifiable.
- **Configuration over hard-coding.** Scientific parameters live in `configs/` and
  are justified after inspecting real data (record ADRs in `docs/decisions/`).
- **No clinical claims.** Use the approved language in the spec (Section 6.5).
- **Approval gates.** Stop and ask before downloading full datasets, deleting/
  overwriting important files, using paid services, publishing, or changing the
  central research question.

## Status

Milestones 0 (repo & environment) and 1 (dataset audit) are complete. No full
datasets downloaded; no models trained. Cohorts (owner-approved): development =
ds007526, external validation = ds002778. Audit findings: both cohorts eyes-open
resting; 31 shared 10-20 channels; see `docs/dataset_audit.md`. Regenerate the audit
with `uv run python scripts/fetch_metadata.py && uv run python scripts/audit_datasets.py`
(metadata only). Next: Milestone 2 (preprocessing), which needs approval to download
raw recordings. See `docs/research_log.md` and `CHANGELOG.md`.
