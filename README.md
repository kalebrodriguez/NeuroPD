# NeuroPD

**Cross-Dataset Validation of Explainable EEG Biomarkers for Parkinson's Disease**

NeuroPD is an open-source, reproducible research pipeline. It asks whether
interpretable resting-state EEG features associated with Parkinson's disease (PD)
generalize **across independent datasets**, recording systems and cohorts. The
emphasis is generalization and biomarker robustness, not maximizing accuracy on a
single dataset.

> **Research tool, not a medical device.** NeuroPD does **not** diagnose
> Parkinson's disease and must never be used for clinical decision-making.

## Start here

- **[Read the manuscript](docs/manuscript.md).** A paper-style draft with figures,
  covering four cohorts and nine pre-specified tests.
- **[Consolidated findings report](docs/report.md).** Every result in one page,
  including what did not hold up.
- **[Research site](https://kalebrodriguez.github.io/NeuroPD/).** The same results
  as interactive pages.
- **[Reproducibility](docs/reproducibility.md).** `make reproduce` re-runs every
  analysis. All 18 committed result sets reproduce exactly.

The manuscript and report are generated from the committed result files. Tests fail
if either is out of date.

## Key findings

- **Site is more predictable than disease.**
  - The same EEG features identify which dataset a recording came from with ROC-AUC
    0.92–0.95, above PD-vs-control transfer in every cohort.
  - The margin is large for ds002778 and ds003490 and narrow for ds004584 (0.92 vs
    0.86).
- **Disease signal transfers to some new sites, not all.** The pre-registered
  relative-power test (ADR 0013):
  - **passed** on ds004584 (AUC 0.733 [0.643, 0.813], n=133);
  - **did not pass** on the smaller ds003490 (0.591 [0.388, 0.785], n=33).
- **Harmonization does not fix this.**
  - ComBat removes per-feature site offsets but does not consistently improve
    transfer (ADR 0014).
  - Leave-one-site-out training does not beat single-site training everywhere
    (ADR 0016).
- **A within-disease association replicates but is fragile.**
  - Among PD participants, a global theta/alpha ratio relates to lower cognition
    (MoCA) at two sites: r = −0.26 and −0.29 (ADR 0017).
  - It fails the pre-declared robustness checks: it is driven by a tail of marked
    slowing, mainly lower alpha (ADR 0018).
- **The conclusions survive the study's two main weaknesses:**
  - dropping ds002778, whose authors advise against classification on it (ADR 0019);
  - loosening artifact rejection (ADR 0020).
- **One of our own explanations was withdrawn.** We had attributed the QC
  sensitivity of transfer to amplitude-sensitive features. That prediction failed
  its pre-declared test (ADR 0021): relative power degraded most.
- **Overall:** two of nine pre-registered or pre-declared tests passed, and all nine
  are reported.

## Research question

Which interpretable resting-state EEG features associated with Parkinson's disease
remain reliable across independent datasets? We expected a measurable within-dataset
association but reduced performance under external validation, because of cohort
and acquisition differences. A weak or null transfer result counts as a meaningful
finding.

## Scientific motivation

Within-dataset machine-learning performance on biomedical EEG often fails to
transfer to a different hospital, device, montage or population. NeuroPD quantifies
that generalization gap with participant-level rigor. It also examines how much
apparent performance is explained by demographics or dataset/site effects rather
than disease.

## Key methodological safeguards

- **Pre-registration:** each confirmatory or sensitivity analysis is written as a
  decision record (`docs/decisions/`) and committed before its result is computed.
- **Participant isolation:** all recordings and sessions from one participant stay
  in a single split, enforced by tests.
- **Frozen external validation:** develop on one cohort, then evaluate once on
  held-out independent cohorts that are never used for supervised tuning.
- **Leakage prevention:** scaling, imputation, selection and harmonization are fitted
  only within training folds.
- **Confound awareness:** demographics-only baselines and age/sex/site analyses.
- **Reproducibility:**
  - a `uv`-locked environment, fixed seeds and saved configs;
  - one command that re-runs and verifies every committed result.

## Datasets

| Role | OpenNeuro | Participants | Condition | License |
|---|---|---|---|---|
| Development | [ds007526](https://openneuro.org/datasets/ds007526) | 144 (116 PD / 28 HC) | resting (eyes-open) + walking | CC0 |
| External validation | [ds002778](https://openneuro.org/datasets/ds002778) | 31 (15 PD / 16 HC) | resting | CC0 |
| Confirmatory (ADR 0013) | [ds004584](https://openneuro.org/datasets/ds004584) | 149 (100 PD / 49 HC) | resting (eyes-open) | CC0 |
| Confirmatory (ADR 0013) | [ds003490](https://openneuro.org/datasets/ds003490) | 50 (25 PD / 25 HC) | rest block (eyes-open part used) + oddball | CC0 |

Counts are before quality control. The post-QC counts used in the analyses (329
participants in total) are in [`docs/report.md`](docs/report.md). All four datasets
are CC0 but carry citation or acknowledgement requests; see
[`docs/dataset_audit.md`](docs/dataset_audit.md).

**No raw or derived participant data are stored in this repository.** Datasets are
downloaded locally into `data/raw/` (git-ignored) only after explicit approval.

## Installation

Requires [`uv`](https://docs.astral.sh/uv/). Python 3.11 is provisioned
automatically.

```bash
git clone https://github.com/kalebrodriguez/neuropd.git
cd neuropd
make install          # uv sync --extra dev
make check            # ruff lint + format check + mypy + pytest (mirrors CI)
```

## Reproducing the results

The committed documents, figures, site and dashboard can be checked without any EEG
data. `make check` fails if the generated report, manuscript or figures disagree
with the committed result files.

Re-running the analyses needs the four datasets in `data/raw/` (git-ignored, about
12 GB; download only with approval, see `scripts/download_openneuro.py`). Then:

```bash
make reproduce        # re-run every analysis from the feature matrices and verify (~40 min)
make reproduce-raw    # the same, starting from raw EEG (preprocessing + features; hours)
```

`make reproduce` (`scripts/reproduce.py`):
- runs every analysis that writes a committed result, in dependency order;
- compares each fresh result with its committed bundle in `dashboard/data/`,
  ignoring generation timestamps;
- reports any difference.

It refuses to run on a working tree with uncommitted changes. The latest run
reproduced 18 of 18 result sets exactly ([`docs/reproducibility.md`](docs/reproducibility.md)).

To rebuild the outputs from the result files:

```bash
uv run python scripts/build_dashboard_data.py   # dashboard/data/ bundles
uv run python scripts/generate_report.py        # docs/report.md
uv run python scripts/generate_manuscript.py    # docs/manuscript.md
uv run python scripts/generate_figures.py       # docs/figures/
uv run python scripts/build_site.py             # site/
uv run streamlit run dashboard/app.py           # local dashboard
```

## Repository structure

```
configs/     dataset, preprocessing, feature and experiment configuration
data/        raw/interim/processed/metadata (git-ignored; never committed)
docs/        manuscript, report, decision records (ADRs), methods, audits, limitations
src/neuropd/ package: data, preprocessing, features, modeling, evaluation, viz
scripts/     pipeline stages, analyses, generators and make reproduce
tests/       unit and integration tests (participant isolation, leakage, staleness, ...)
dashboard/   Streamlit app and its committed, de-identified data bundles
site/        static research site (GitHub Pages)
```

## Project history

Each release is audited ([`docs/audit.md`](docs/audit.md)). Details are in
[`CHANGELOG.md`](CHANGELOG.md) and the decision records.

- **v0.1.0 (Milestones 0–8):**
  - the pipeline, internal and external baselines, explainability and the dataset
    shift analysis;
  - the dashboard and static site.
  - Initial finding: dataset identity (AUC ≈ 0.95) far exceeds disease on the first
    two cohorts.
- **v0.2.0:**
  - sensitivity analyses (ADR 0010);
  - two pre-registered confirmatory cohorts (ADR 0013);
  - ComBat harmonization (ADR 0014);
  - a peak-separated 1/f fit (ADR 0015).
- **v0.3.0:** leave-one-site-out training (ADR 0016), and a pre-registered within-PD
  cognition replication (ADR 0017).
- **v0.4.0:** its robustness checks (ADR 0018, not robust), and a manuscript draft
  with figures.
- **v0.5.0:** the conclusions hold without ds002778 (ADR 0019) and with a lenient
  artifact threshold (ADR 0020).
- **v0.5.1:** the explanation offered for ADR 0020 failed its pre-declared test
  (ADR 0021) and was withdrawn.
- **Since v0.5.1:**
  - `make reproduce`;
  - the remaining v0.1.0-era results refreshed to the current 230-feature pipeline
    (no conclusion changed);
  - a full verification run, 18/18 exact.

### How the conclusions changed along the way

- **ADR 0010: "only normalized features transfer".** The first external cohort
  (ds002778, n=30) suggested that relative band power transfers well (AUC ≈ 0.87)
  while scale-sensitive features do not. This did **not** hold on the larger
  pre-registered cohort ds004584, where every feature family transferred about
  equally (AUC 0.72–0.75) (ADR 0013).
- **ADR 0016: per-site standardization helps the small sites.** This looked
  promising: ds003490 went from 0.532 to 0.663. With ds002778 removed from training,
  the gain shrinks to +0.05 (ADR 0019). It remains directional.
- **ADR 0020: amplitude-sensitive features absorb artifact.** This interpretation was
  tested in ADR 0021 and not supported.

## Analyses in detail

Each analysis has a decision record in `docs/decisions/` and a results document:

| analysis | decision record | results |
| --- | --- | --- |
| internal and external baselines, dataset shift | ADRs 0005–0009 | [`internal_baselines`](docs/internal_baselines.md), [`external_transfer`](docs/external_transfer.md), [`dataset_shift`](docs/dataset_shift.md) |
| sensitivity analyses | ADR 0010 | [`sensitivity`](docs/sensitivity.md) |
| per-cohort harmonization, aperiodic (1/f) features | ADRs 0011–0012 | [`harmonization`](docs/harmonization.md) |
| confirmatory transfer | ADR 0013 | [`confirmatory_transfer`](docs/confirmatory_transfer.md) |
| ComBat harmonization | ADR 0014 | [`combat`](docs/combat.md) |
| peak-separated aperiodic fit | ADR 0015 | [`aperiodic_specparam`](docs/aperiodic_specparam.md) |
| leave-one-site-out training | ADR 0016 | [`multisite`](docs/multisite.md) |
| within-PD cognition | ADRs 0017–0018 | [`clinical`](docs/clinical.md), [`clinical_robustness`](docs/clinical_robustness.md) |
| without ds002778 | ADR 0019 | [`without_ds002778`](docs/without_ds002778.md) |
| QC threshold | ADRs 0020–0021 | [`qc_threshold`](docs/qc_threshold.md), [`qc_by_family`](docs/qc_by_family.md) |

**Deployment.** The static site is generated by `scripts/build_site.py` from
de-identified outputs. It auto-deploys to GitHub Pages via
`.github/workflows/pages.yml`. The Streamlit dashboard is Heroku-ready (`Procfile`,
`requirements.txt`). Both use only precomputed, de-identified data: no raw EEG, no
uploads and no diagnosis. See [`docs/deployment.md`](docs/deployment.md).

## Limitations

The study is limited by:
- small external cohorts (n=30 and n=33);
- an imbalanced development cohort with an age/sex confound;
- cross-dataset differences in acquisition and conditions;
- the retrospective, public-dataset design.

See [`docs/limitations.md`](docs/limitations.md).

## Citation and license

Source code is released under the [MIT License](LICENSE). If you use NeuroPD, please
cite this repository (see [`CITATION.cff`](CITATION.cff)) **and** the underlying
datasets. Before publishing any findings that use ds002778, contact its authors as
they request (`arockhil@uoregon.edu`).
