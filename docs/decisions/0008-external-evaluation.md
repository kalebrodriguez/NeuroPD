# ADR 0008: Frozen external-transfer evaluation

- **Date:** 2026-07-24
- **Status:** accepted

## Context
Milestone 5 is the central test of the project (spec Section 3): do interpretable
EEG features that separate PD from HC within one cohort **transfer** to an
independent cohort? The pipeline and analysis plan were frozen first (ADRs
0005-0007); the external cohort was untouched through Milestone 4.

## Decision
- **Primary experiment:** fit each frozen baseline on the **entire** development
  cohort (ds007526, 133 participants) and evaluate **once** on the **entire**
  external cohort (ds002778, 30 participants). No tuning uses the external cohort.
- **Harmonization:** the shared 31-channel, region-level feature matrix is already
  cross-cohort comparable (ADR 0006), so both cohorts use identical 210 features.
- **Reporting:** external metrics with 95% participant-level bootstrap CIs; the
  **generalization gap** = internal (cross-validated) minus external balanced
  accuracy; Brier score for probability models.
- **Reverse direction (ds002778 -> ds007526):** run as a **separate, exploratory**
  experiment only (Section 6.2). The ds002778 authors caution against small-sample
  classification, so its internal CV (n=30) is unstable and not emphasized.

## Results (executed, primary direction ds007526 -> ds002778)
| model | external bal acc [95% CI] | external AUC | internal bal acc |
|---|---|---|---|
| majority | 0.500 | 0.500 | 0.500 |
| demographics (age+sex) | 0.500 [0.33, 0.68] | 0.538 | 0.645 |
| logreg (EEG) | 0.667 [0.50, 0.83] | 0.671 | 0.563 |
| svm_linear (EEG) | 0.633 [0.46, 0.80] | 0.653 | 0.558 |
| random_forest (EEG) | 0.533 [0.40, 0.67] | 0.738 | 0.591 |

## Interpretation (honest, non-clinical)
1. **The demographic confound does not transfer.** Age/sex reached 0.645 balanced
   accuracy within ds007526 (where PD are older and more male) but fell to **chance
   (0.500)** on the age/sex-balanced ds002778. This confirms the internal
   demographics signal (ADR 0007) was cohort-specific confounding, not a
   generalizable predictor — a key, hypothesis-consistent finding.
2. **Linear EEG models show modest, directionally consistent transfer.** Logistic
   regression and linear SVM held ~0.63-0.67 external balanced accuracy (and did not
   degrade versus internal), suggesting some cross-cohort robustness of interpretable
   spectral/complexity features. **However**, with only 30 external participants the
   CIs are wide and include chance, so this is **not statistically conclusive**.
3. **The random forest generalizes worst on decision-level accuracy** (largest
   positive gap; high AUC but poor external balanced accuracy), consistent with the
   expectation that simpler models are more reliable under external validation
   (Section 3.2 Q4).

## Consequences
- The primary conclusion is nuanced, not a clean success or null: interpretable
  linear EEG models transfer better than a demographic confound and better than a
  complex model, but the external sample is too small for a definitive claim. This
  is reported as-is (no optimization toward a desired result, Section 3.3).
- Next: explainability + sensitivity analyses (Milestone 6) — feature-importance
  stability across folds/datasets, age/sex-adjusted and channel-harmonization
  sensitivity, and unsupervised dataset-shift checks (Section 16).
