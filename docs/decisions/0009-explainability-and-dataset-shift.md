# ADR 0009: Explainability and unsupervised dataset-shift analysis

- **Date:** 2026-07-24
- **Status:** accepted

## Context
Milestone 6 must interpret the transfer results (spec Sections 15-16) without
claiming biological causation, and test whether dataset identity confounds the
feature space (failure mode Section 28.3).

## Decision
- **Feature importance:** standardized logistic-regression coefficients (the
  pipeline standardizes first, so magnitudes are comparable) averaged over 5x5
  stratified grouped CV folds, with per-feature **std** and **sign consistency** as
  stability measures, a **region x frequency** aggregation, and **cross-dataset
  agreement** (Pearson r of per-feature mean coefficients estimated independently on
  each cohort).
- **Dataset-shift:** train logistic-regression and random-forest classifiers to
  predict **dataset identity** (ds007526 vs ds002778) from the same shared 210
  features, under participant-grouped CV, and compare to disease predictability.
- SHAP and UMAP were **not** used: linear standardized coefficients are directly
  interpretable at this scale, and UMAP clustering must not be read as biological
  subtypes (Section 16). Permutation importance for the random forest is deferred.

## Results (executed)
- **Cross-dataset importance agreement: Pearson r = +0.045** — essentially zero. The
  logistic model relies on different features in each cohort.
- **Dataset-identity prediction: logistic regression balanced accuracy 0.833,
  ROC-AUC 0.953; random forest AUC 0.894** — far above disease predictability
  (~0.72 internal, ~0.65 external, Milestones 4-5).
- Top disease features on ds007526 are fold-stable (sign consistency 1.0) and
  dominated by within-participant variability (IQR) of occipital/frontal
  theta/beta power and peak-alpha-frequency spread.

## Interpretation (the central methodological result)
**Dataset identity is far easier to predict than Parkinson's disease** (AUC ~0.95
vs ~0.72), and the disease-predictive features **do not agree across cohorts**
(r ≈ 0). Together these show the shared EEG feature space is dominated by
site/acquisition differences (hardware, montage, population, line frequency) rather
than disease physiology. This is the project's key transparency finding: it
explains the limited cross-cohort transfer in Milestone 5 and demonstrates
concretely how within-cohort biomarker performance can fail to generalize. It is a
methodological result about dataset shift, **not** a claim about brain biology.

## Consequences
- Any future biomarker claim must be conditioned on dataset-shift control (e.g.
  harmonization such as ComBat, site-adjusted models, or matched cohorts) — logged
  as a stretch goal, not implemented here.
- Remaining M6 sensitivity analyses (shared-channel vs region features, age/sex
  adjustment, alternative preprocessing) are proposed for a follow-up; the
  dataset-shift result is the priority finding and is reported now.
