# ADR 0007: Internal cross-validation design and primary metric

- **Date:** 2026-07-23
- **Status:** accepted

## Context
Milestone 4 evaluates baseline models on the development cohort (ds007526: 133
participants after QC, 27 HC / 106 PD, ~4:1 imbalance). The design must prevent
participant leakage (spec Section 6.1), fit all transforms inside training folds
(Section 6.3), and avoid overfitting a small, imbalanced sample (Section 13.2).

## Decision
- **Cross-validation:** repeated **stratified, grouped** k-fold keyed by
  participant — `n_splits=5`, `n_repeats=5` (25 fits/model). One row per
  participant, but grouping is enforced and each fold is checked against
  `assert_participants_disjoint`. 5 folds keep ~5-6 HC per test fold.
- **Minimal tuning (flat CV, not nested):** fixed, sensible hyperparameters
  (L2 logistic regression, linear SVM, 400-tree random forest), all with
  `class_weight="balanced"` fitted on the training fold. With n=133 and 4:1
  imbalance, heavy hyperparameter search risks overfitting (Section 13.2); nested
  CV is deferred unless a model clearly needs tuning.
- **Primary metric: balanced accuracy** (Section 14.1), with ROC-AUC, sensitivity,
  specificity, and F1 reported alongside. Plain accuracy is never used.
- **Uncertainty:** 95% **participant-level bootstrap** percentile CIs (2000
  resamples of participants, not epochs) on out-of-fold predictions.
- **Class imbalance:** handled by class weighting fitted within folds; no SMOTE,
  no resampling of the full dataset (Section 13.3).
- **The external cohort (ds002778) is not touched** in Milestone 4 (Section 6.2).

## Alternatives
- **Nested CV** — deferred; tuning is intentionally minimal here.
- **ROC-AUC as primary** — AUC is threshold-free and reported, but balanced
  accuracy is the decision-level summary the study commits to; both are shown.
- **Leave-one-participant-out** — higher variance and cost with little benefit at
  this n; repeated 5-fold is more stable.

## Consequences / first result
- Running the baselines produced a **material confound finding**: the
  **demographics-only** model (age + sex) reached balanced accuracy ≈ 0.65,
  **exceeding every EEG model** (≈ 0.56-0.59), while EEG models ranked somewhat
  better on AUC (random forest ≈ 0.76 vs demographics ≈ 0.69). Because ds007526 PD
  are older and more male than HC, age/sex alone carry substantial signal. This is
  reported honestly and means EEG performance must be interpreted **against** the
  demographics baseline, and motivates age/sex-adjusted sensitivity analyses
  (Section 6.4) and the external-transfer test (Milestone 5). It is not evidence
  that EEG features are useless — it is evidence that within-cohort separation is
  partly confounded.
