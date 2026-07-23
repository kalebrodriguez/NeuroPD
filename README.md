# NeuroPD

**Cross-Dataset Validation of Explainable EEG Biomarkers for Parkinson's Disease**

NeuroPD is an open-source, reproducible research pipeline for studying whether
interpretable resting-state EEG features associated with Parkinson's disease (PD)
generalize **across independent datasets**, recording systems, and cohorts. The
scientific emphasis is generalization and biomarker robustness — not maximizing
accuracy on a single dataset.

> **Research tool, not a medical device.** NeuroPD does **not** diagnose
> Parkinson's disease and must never be used for clinical decision-making.

## Research question

Which interpretable resting-state EEG features associated with Parkinson's
disease remain reliable across independent datasets? We expect measurable
within-dataset association but reduced performance under external validation due
to cohort and acquisition differences — and we treat a weak or null transfer
result as a scientifically meaningful finding.

## Scientific motivation

Within-dataset machine-learning performance on biomedical EEG often fails to
transfer to a different hospital, device, montage, or population. NeuroPD
quantifies that generalization gap with participant-level rigor, and examines how
much apparent performance is explained by demographics or dataset/site effects
rather than disease.

## Key methodological safeguards

- **Participant isolation:** all recordings/sessions from one participant stay in
  a single split; enforced by tests.
- **Frozen external validation:** develop on one cohort, evaluate transfer on a
  held-out independent cohort that is never used for supervised tuning.
- **Leakage prevention:** scaling, imputation, selection, and harmonization are
  fitted only within training folds.
- **Confound awareness:** demographics-only baselines and age/sex/site analyses.
- **Reproducibility:** `uv`-locked environment, fixed seeds, saved configs, and
  recorded software/provenance.

## Datasets

| Role | OpenNeuro | Participants | Condition | License |
|---|---|---|---|---|
| Development | [ds007526](https://openneuro.org/datasets/ds007526) | 144 (116 PD / 28 HC) | resting (eyes-open) + walking | CC0 |
| External validation | [ds002778](https://openneuro.org/datasets/ds002778) | 31 (15 PD / 16 HC) | resting | CC0 |

Both are CC0 but carry citation/acknowledgement requests; see
[`docs/dataset_audit.md`](docs/dataset_audit.md). **No raw or derived participant
data are stored in this repository.** Datasets are downloaded locally into
`data/raw/` (git-ignored) only after explicit approval.

## Installation

Requires [`uv`](https://docs.astral.sh/uv/); Python 3.11 is provisioned automatically.

```bash
git clone https://github.com/kalebrodriguez/neuropd.git
cd neuropd
make install          # uv sync --extra dev
make check            # ruff + mypy + pytest
uv run neuropd --help
```

## Reproduction commands

Data acquisition and analysis commands are added milestone by milestone. Current
entry points:

```bash
uv run neuropd provenance      # print versions/platform/seed provenance record
```

Planned CLI/scripts (see `scripts/`): dataset audit, preprocessing, feature
extraction, training, external evaluation, and reporting.

## Repository structure

```
configs/     dataset, preprocessing, feature, and experiment configuration
data/        raw/interim/processed/metadata (git-ignored; never committed)
docs/        methods, decision records, neuroscience notes, audit, limitations
src/neuropd/ package: data, preprocessing, features, modeling, evaluation, viz
scripts/     command-line pipeline stages
tests/       unit/integration tests (participant isolation, smoke, ...)
dashboard/   educational Streamlit app (built after the pipeline is validated)
```

## Current status

**Milestone 2 (raw download + preprocessing): complete** (pending owner review).
Raw data were downloaded (owner-approved) into git-ignored `data/raw/` with
checksums and provenance; a configurable conservative pipeline harmonizes both
cohorts to **31 shared channels**, filters/notches/resamples/re-references, epochs,
and rejects artifacts with QC. See [`docs/dataset_audit.md`](docs/dataset_audit.md)
and [`docs/decisions/`](docs/decisions/). No models trained yet. Next: Milestone 3
(interpretable features).

Run preprocessing (after downloading raw data): `uv run python scripts/preprocess.py --figures`.

## Limitations

Small sample sizes (especially the external cohort), cross-dataset differences in
acquisition and conditions, and the retrospective, public-dataset nature of the
study limit the scope of any conclusions. See
[`docs/limitations.md`](docs/limitations.md).

## Citation and license

Source code is released under the [MIT License](LICENSE). If you use NeuroPD,
please cite this repository (see [`CITATION.cff`](CITATION.cff)) **and** the
underlying datasets. Before publishing any findings that use ds002778, contact
its authors as they request (`arockhil@uoregon.edu`).

## AI-use disclosure

This project uses AI assistance (documented in [`AI_USAGE.md`](AI_USAGE.md)). All
factual claims, citations, and reported results are verified against real sources
and executed code.
