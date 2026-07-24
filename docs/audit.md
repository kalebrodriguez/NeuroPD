# Milestone 8 — Final Audit

Date: 2026-07-24. Audits the repository against the spec's completion standard
(Section 22 Milestone 8, Section 25, Section 31) before the `v0.1.0` release
candidate. Every check below was executed.

## Reproducibility audit

- **Environment locked:** `pyproject.toml`, `uv.lock`, `.python-version` (3.11) all
  present; dev tools are an optional group (`uv sync --extra dev`).
- **Determinism:** a central seed (`configs/project.yaml`, `DEFAULT_SEED=20240517`)
  is threaded through every stochastic step (CV shuffles, model `random_state`,
  bootstrap RNG).
- **Config-driven:** dataset, preprocessing, feature, and experiment parameters live
  in `configs/`, validated by Pydantic models that reject unknown keys.
- **Reproduction path (documented in README):** download → `preprocess.py` →
  `qc_report.py` → `extract_features.py` → `train.py` → `evaluate_external.py` →
  `explain.py` → `build_dashboard_data.py` → `streamlit run dashboard/app.py`.
- **CI:** GitHub Actions runs `ruff format --check`, `ruff check`, `mypy`, and
  `pytest` on every push, without downloading datasets. Status: green.
- **Tests:** 69 pass / 0 skip, including participant-isolation, no-leakage
  (scaler-in-fold, no id/label in the feature matrix), synthetic-signal feature
  checks, metrics toy examples, CV group-disjointness, and a headless dashboard run.

## Scientific-claims audit

Every headline number was re-verified against the executed `dashboard/data/metrics.json`:

| claim | source value |
|---|---|
| dataset-identity ROC-AUC ≈ 0.95 | 0.953 |
| dataset-identity balanced acc 0.833 | 0.833 |
| internal demographics balanced acc 0.645 | 0.645 |
| internal random-forest AUC 0.759 | 0.759 |
| external demographics balanced acc 0.500 | 0.500 |
| external logreg balanced acc 0.667 | 0.667 |

- No performance claim is stated that is not produced by executed code.
- Disallowed clinical language (Section 6.5) is not used; results are framed as
  research findings about cross-dataset robustness, never diagnosis.
- Predictive feature importance is explicitly distinguished from biological causation.

## Security / privacy audit

- **No raw or derived EEG is tracked in Git.** `git ls-files` shows only
  `data/raw/.gitkeep` under `data/`; no `.fif/.bdf/.set/.edf/.parquet`.
- **No secrets:** no `.env`, key, credential, or token files are tracked; `.env` is
  git-ignored and only `.env.example` exists.
- **Dashboard data is de-identified:** `dashboard/data/biomarkers.csv` carries no
  `participant_id` (enforced by a test); only dataset/group labels and derived
  feature values from public CC0 datasets.
- **No re-identification, no upload/prediction feature, no controlled-access data.**

## Credits / licensing audit

- Code: MIT (`LICENSE`). Datasets: CC0, cited with DOIs in `CITATION.cff`,
  `docs/dataset_audit.md`, and the README, including the ds002778 authors'
  pre-publication contact request.
- Software (MNE-Python, scikit-learn, NumPy/pandas/SciPy, Streamlit, etc.) is
  declared in `pyproject.toml`.

## AI-use note

Per the project owner, the `AI_USAGE.md` provenance file and README AI-use
disclosure were removed at their request; this is an owner decision for a personal
research/portfolio repository. If the work is later submitted where AI-use
disclosure is required, that line should be reinstated.

## Outcome

All Milestone 8 acceptance criteria are met: CI/tests pass, no secrets or raw data
are committed, all claims trace to executed analyses, and external data and software
are credited. Tagged as release candidate **v0.1.0**.
