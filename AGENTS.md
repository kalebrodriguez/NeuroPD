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

Milestones 0–8 are complete and `v0.1.0` is tagged; `v0.2.0` (audited,
`docs/audit.md`) adds the work below; deployment (GitHub Pages site +
Heroku-ready dashboard), sensitivity analyses (ADR 0010) and the harmonization +
aperiodic stretch work (ADRs 0011–0012) have since been merged. Cohorts
(owner-approved): development = ds007526, external validation = ds002778,
confirmatory = ds004584, ds003490. Raw and
derived data are git-ignored, so a fresh clone/container has **no EEG data**;
re-running the pipeline requires re-downloading the cohorts (approval gate). Confirmatory
cohort ds004584 was added under a pre-registered plan (ADR 0013): H1 confirmed
(relative-power AUC 0.733), with all feature families transferring similarly. On
ds003490 H1 was not confirmed (AUC 0.591, n=33, inconclusive). Dataset identity
stays far more predictable than disease. ComBat harmonization
(ADR 0014) removes site offsets without consistently improving transfer. A
peak-separated aperiodic fit (ADR 0015; `fooof` 1.1.1) shows the PD exponent effect
is partly peak contamination and does not improve transfer. The site and dashboard
include these results ("New cohorts" page). Leave-one-site-out training (ADR 0016)
does not beat single-site training at every site (H2 not supported). With per-site
standardization it improves the two small sites (directional). Within PD, a global
theta/alpha ratio relates to poorer MoCA at both severity sites (ADR 0017,
pre-registered; r ≈ −0.27, replicated). Occipital PAF does not. See `docs/research_log.md`,
`docs/audit.md` and `CHANGELOG.md`.
