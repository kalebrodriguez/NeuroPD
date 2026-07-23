# Changelog

All notable changes to NeuroPD are documented here. The format is loosely based
on [Keep a Changelog](https://keepachangelog.com/), and the project follows
milestone-based development (spec Section 22).

## [Unreleased]

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
