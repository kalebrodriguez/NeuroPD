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
| Confirmatory (ADR 0013) | [ds004584](https://openneuro.org/datasets/ds004584) | 149 (100 PD / 49 HC) | resting (eyes-open) | CC0 |
| Confirmatory (ADR 0013) | [ds003490](https://openneuro.org/datasets/ds003490) | 50 (25 PD / 25 HC) | rest block (eyes-open part used) + oddball | CC0 |

All four are CC0 but carry citation/acknowledgement requests; see
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

**Milestones 0–8 complete + deployed** (v0.1.0). **v0.2.0** adds sensitivity
analyses, two pre-registered confirmatory cohorts, ComBat harmonization and a
peak-separated 1/f fit. A 7-page Streamlit dashboard (`dashboard/app.py`) and an
8-page static site (`site/`, live on GitHub Pages) communicate the results, reading **only**
committed, de-identified derived data (no raw EEG, no participant ids) with a
non-diagnostic disclaimer on every page.

**Central finding:** **dataset identity is predicted at ROC-AUC ≈ 0.95**, far above
disease (≈ 0.72 internal, ≈ 0.65 external), and disease feature-importance does not
agree across cohorts (r ≈ 0.05) — the shared feature space is dominated by
site/acquisition differences. **Sensitivity analyses sharpen this** (see
[`docs/sensitivity.md`](docs/sensitivity.md) / ADR 0010): region-level features
transfer while exact-channel features collapse to chance; EEG retains signal after
age/sex are partialled out (AUC ≈ 0.67); and **relative (normalized) band power
transfers well (external AUC ≈ 0.87)** while scale-sensitive features do not. So the
honest conclusion is *modest, normalization-dependent* cross-dataset transfer — not a
flat null — though the small external cohort (n=30) keeps it directional, not
conclusive.

**Pre-registered confirmation on a new cohort (ADR 0013):** the relative-power test
was fixed and committed *before* any new data was downloaded, then run once on
**ds004584** (Univ. of Iowa, n=133 after QC, 89 PD). It **passed**: external AUC
**0.733 [0.643, 0.813]**, and 0.740 [0.651, 0.820] in the PO3/PO4 sensitivity check.
But relative power is *not* special there: every feature family transfers
similarly (AUC 0.72–0.75) and the all-feature logreg reaches 0.857, while age/sex
alone is at chance (0.46). The "normalization-dependent" refinement from ds002778
does not hold up; the broader claim, that ds007526-trained EEG features carry some
disease signal to a new site, does. Site differences remain large (dataset identity
AUC 0.92).

On the second pre-registered cohort, **ds003490** (Univ. of New Mexico; n=33
after QC, only ~1 min of eyes-open EEG each), the test **did not pass**: AUC
**0.591 [0.388, 0.785]**. That interval is too wide to show either transfer or its
absence. Overall, disease signal transfers clearly to the largest new site but
not reliably to every site. See
[`docs/confirmatory_transfer.md`](docs/confirmatory_transfer.md).

**ComBat harmonization (ADR 0014):** an empirical-Bayes ComBat (checked against
`neuroCombat`), with and without protecting age/sex, removes the per-feature site
differences (dataset identity no longer separable). It does **not** consistently
improve disease transfer across the three external cohorts (logreg AUC moves by
≤ 0.04, all within CIs), which fails its pre-declared criterion. See
[`docs/combat.md`](docs/combat.md).

**Peak-separated aperiodic fit (ADR 0015):** spectral parameterization (`fooof`
1.1.1, the stable release of `specparam`) fits well (median R² 0.95–0.99). The
steeper 1/f exponent in PD seen with a plain log-log fit **shrinks** once
oscillatory peaks are modelled, but stays clear in ds004584 (d 0.52 [0.18, 0.89]).
The development cohort shows no exponent difference, so the aperiodic features do
not improve cross-site transfer either way. See
[`docs/aperiodic_specparam.md`](docs/aperiodic_specparam.md).

**Stretch extensions (ADR 0011/0012):** train-safe **per-cohort harmonization**
does **not** improve cross-dataset transfer (external balanced accuracy stays
≈ 0.60–0.66), indicating the site effect is higher-order than a global scale/shift;
and an **aperiodic (1/f)** feature was added (230 features) without changing
transfer — both informative negative results. See
[`docs/harmonization.md`](docs/harmonization.md).

**Leave-one-site-out multi-site training (ADR 0016, pre-declared):** training on
three sites and testing on the fourth does **not** beat the single-site model at
every site, so the pre-declared criterion is not met: ds004584 stays at about
0.84-0.86. With **per-site standardization**, multi-site training improves
transfer to the two small sites: ds002778 0.720 → 0.813, ds003490 0.532 → 0.663.
This is directional, with overlapping CIs. See
[`docs/multisite.md`](docs/multisite.md).

**Deployment (v0.1.0):** a static research site (`site/index.html`, generated by
`scripts/build_site.py` from de-identified outputs) auto-deploys to **GitHub Pages**
via `.github/workflows/pages.yml` → `https://kalebrodriguez.github.io/NeuroPD/`; the
interactive Streamlit dashboard is Heroku-ready (`Procfile`, `requirements.txt`). Both
use only precomputed, de-identified data — no raw EEG, no uploads, no diagnosis. See
[`docs/deployment.md`](docs/deployment.md).

Reproduce (after downloading raw data):
`scripts/preprocess.py --limit-per-group 0` → `scripts/qc_report.py` →
`scripts/extract_features.py` → `scripts/train.py` →
`scripts/evaluate_external.py --bidirectional` → `scripts/explain.py` →
`scripts/build_dashboard_data.py` → `scripts/build_site.py` (each via
`uv run python`), then `uv run streamlit run dashboard/app.py` for the local dashboard.

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
