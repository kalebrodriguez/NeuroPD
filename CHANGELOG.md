# Changelog

All notable changes to NeuroPD are documented here. The format is loosely based
on [Keep a Changelog](https://keepachangelog.com/), and the project follows
milestone-based development (spec Section 22).

## [Unreleased]

### Added (stretch: harmonization + aperiodic)
- Train-safe per-cohort feature harmonization (`neuropd.modeling.harmonization`,
  `evaluate_external.py --harmonize`; ADR 0011) and the aperiodic 1/f spectral
  feature (`spectral.aperiodic_fit`; ADR 0012), with offline tests.
- Results in `docs/harmonization.md`: harmonization does not improve transfer and
  aperiodic features leave transfer unchanged (informative negative results).

### Added (sensitivity analyses + multi-page site)
- `scripts/sensitivity.py` + ADR 0010 + `docs/sensitivity.md`: harmonization
  (region vs channel), age/sex in-fold residualization, and feature-family analyses.
  `extract_features.py` gains `--spatial channel`.
- **Findings:** region features transfer (external AUC 0.67) but channel-level do not
  (0.53); EEG residualized on age/sex stays above chance (AUC 0.67) — signal beyond
  demographics; **relative band power transfers best (external AUC 0.87)** vs
  absolute/log/slowing/complexity — the headline sharpens to *normalization-dependent*
  transfer. All external estimates are n=30 (directional).
- `build_site.py` rewritten as a 7-page static site (overview, datasets, biomarkers
  with SVG box plots, results, dataset-shift, sensitivity, methods) with shared nav;
  `explain.py` emits `feature_importance.json`; dashboard-data builder bundles both.

### Fixed
- GitHub Pages: reset to workflow-only source so the deploy workflow (not the legacy
  Jekyll builder) publishes the site.

### Added (deployment)
- Static GitHub Pages research site: `scripts/build_site.py` generates a
  self-contained `site/index.html` from de-identified outputs; `.github/workflows/pages.yml`
  publishes it. Heroku-ready Streamlit dashboard (`Procfile`, `requirements.txt`,
  `runtime.txt`, `.streamlit/config.toml`). `docs/deployment.md`; a test asserts the
  published site carries no participant id and shows the non-diagnostic disclaimer.

## [0.1.0] — 2026-07-24

First release candidate (Milestone 8 audit passed). Complete cross-dataset
investigation: dataset audit → tested preprocessing → interpretable features →
participant-safe internal baselines → frozen external evaluation → explainability
and dataset-shift analysis → educational dashboard. Central finding: dataset
identity is far more predictable than disease (AUC ~0.95 vs ~0.72), so the shared
EEG feature space is dominated by site/acquisition differences — biomarkers show
only modest, not-yet-conclusive cross-cohort transfer. See `docs/audit.md`.

### Added (Milestone 8 — final audit)
- `docs/audit.md` (reproducibility, scientific-claims, security/privacy, credits
  audits); version bumped to 0.1.0 (`pyproject.toml`, `CITATION.cff`).

### Added (Milestone 7 — educational dashboard)
- `scripts/build_dashboard_data.py` producing committed, **de-identified** dashboard
  artifacts (`dashboard/data/`: metrics.json, cohorts.json, biomarkers.csv with no
  participant ids); JSON output added to `scripts/explain.py`.
- `dashboard/app.py` rewritten as a 6-page Streamlit app (overview, dataset explorer,
  biomarker explorer, model evaluation, generalization gap + dataset-shift, methods)
  reading only the committed derived data, with a non-diagnostic disclaimer on every
  page; `tests/test_dashboard.py` (headless AppTest across all pages; 69 pass / 0 skip).
- Not deployed — GitHub Pages / Heroku deployment remains a separate owner-approved step.

### Added (Milestone 6 — explainability + dataset-shift)
- `modeling/explainability.py` (fold-stable standardized logistic-regression
  coefficients, region×frequency importance aggregation, cross-dataset agreement),
  `scripts/explain.py`, ADR 0009, committed `docs/explainability.md` and
  `docs/dataset_shift.md`, `tests/test_explainability.py` (62 pass / 0 skip).
- **Key finding:** dataset identity is predicted at ROC-AUC ~0.95 (vs disease ~0.72),
  and disease feature-importance does not agree across cohorts (r ≈ 0.05) — the shared
  EEG feature space is dominated by site/acquisition differences, not disease
  physiology, explaining the limited transfer. Reported as a dataset-shift result, not
  a biological claim.

### Added (Milestone 5 — frozen external evaluation)
- `evaluation/transfer.py` (fit on the full development cohort, evaluate once on the
  full external cohort; generalization gap), `modeling/calibration.py` (Brier score +
  reliability curve), and `neuropd/data/demographics.py` (shared age/sex loader).
- `scripts/evaluate_external.py` (bidirectional, external cohort never tuned on),
  ADR 0008, committed results `docs/external_transfer.md`, `tests/test_transfer.py`.
- Result (ds007526 → ds002778): the demographics confound does **not** transfer
  (0.645 → 0.500 chance); linear EEG models transfer modestly (~0.63–0.67 external
  balanced accuracy) but external n=30 CIs include chance (not conclusive); random
  forest generalizes worst on decision accuracy.

### Added (Milestone 4 — internal baselines)
- `evaluation/metrics.py` (balanced accuracy, ROC-AUC, sensitivity, specificity,
  F1, confusion counts; PD = positive class) and `evaluation/bootstrap.py`
  (participant-level bootstrap confidence intervals).
- `modeling/baselines.py` (majority, demographics-only, regularized logistic
  regression, linear SVM, random forest — each an sklearn Pipeline with in-fold
  imputation/scaling and balanced class weights) and `modeling/pipeline.py`
  (repeated stratified grouped CV keyed by participant, asserting participant
  disjointness per fold).
- `scripts/train.py`, ADR 0007 (CV design + primary metric), committed results
  `docs/internal_baselines.md`; tests `test_metrics.py`, `test_modeling.py`, and the
  scaler-in-fold leakage test (56 pass / 0 skip).
- Internal result (ds007526): demographics-only balanced accuracy (~0.65) exceeds
  the EEG models (~0.56-0.59); random forest AUC ~0.76 — documented age/sex confound.

### Added (Milestone 3 — interpretable features)
- Feature package (`neuropd.features`): `spectral` (Welch PSD; absolute/relative/log
  band power, peak alpha frequency, spectral edge frequency, theta/alpha & delta/alpha
  slowing ratios, spectral entropy), `complexity` (Hjorth parameters, permutation
  entropy), `aggregate` (epoch×channel base features → region-level aggregation →
  per-participant median/IQR), and `matrix` (one-row-per-participant assembly with
  identifiers/labels kept separate from features).
- `FeatureConfig` validation and `configs/features/interpretable.yaml` (PSD params,
  band boundaries, region spatial strategy; gamma disabled with justification).
- `scripts/extract_features.py` (processed epochs → participant feature matrix,
  sessions pooled) and `scripts/qc_report.py` (committed QC/exclusion report).
- Docs: ADR 0006, `docs/feature_dictionary.md`, `docs/preprocessing_qc.md`;
  synthetic-signal + leakage tests (`tests/test_features.py`, `tests/test_no_leakage.py`).
- Full-cohort feature matrices: ds007526 (133 participants) and ds002778 (30), each
  210 region-level features, 0 missing cells.

### Removed
- `AI_USAGE.md` and the README AI-use disclosure (owner request).

### Added (Milestone 2 — raw download + preprocessing)
- Approval-gated raw-dataset downloader (`download_dataset`) with checksums,
  read-only immutability, and committed provenance (`docs/data_provenance.md`).
- Recording loaders (`neuropd.data.loaders`) and a configurable, conservative
  preprocessing pipeline (`neuropd.preprocessing.*`): 31-channel harmonization,
  standard montage, per-dataset notch (ADR 0004), 1-40 Hz band-pass, resample to
  250 Hz, average reference, 2 s epochs, amplitude rejection, and predeclared
  exclusion with QC metrics.
- `PreprocessingConfig` (validated); `conservative`/`sensitivity` profiles;
  `configs/harmonization.yaml` (31 shared channels).
- `scripts/preprocess.py`; QC tables + PSD figures; synthetic-signal tests
  (`tests/test_preprocessing.py`); ADR 0005.

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
- Governance and documentation: `README`, `LICENSE`, `CITATION.cff`,
  `CONTRIBUTING.md`, `docs/research_log.md`, initial decision records, and
  neuroscience/limitations doc stubs.
- Tooling: `Makefile`, ruff/mypy configuration, pytest suite, and GitHub Actions
  CI that runs lint/typecheck/tests without downloading datasets.
- Verified, versioned dataset configuration for ds002778 and ds007526 (audited
  metadata only; scientific parameters flagged for Milestone 1 verification).
