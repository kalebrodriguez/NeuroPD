# ADR 0014: Empirical-Bayes ComBat harmonization (pre-declared)

- **Date:** 2026-11-08
- **Status:** accepted (written and committed before any ComBat result was computed)

## Context
Per-cohort z-scoring (ADR 0011) did not improve cross-site transfer. ComBat
(Johnson, Li & Rabinovic 2007, *Biostatistics* 8:118-127; applied to neuroimaging
by Fortin et al. 2017/2018) is the standard batch-correction method. Compared with
per-cohort z-scoring it adds two things:

1. **Empirical-Bayes shrinkage.** Each feature's per-cohort location and scale are
   pulled toward a prior pooled across features, which stabilises them in small
   cohorts (ds002778 n=30, ds003490 n=33).
2. **Covariate preservation.** Effects of chosen covariates (here age and sex) are
   estimated and kept while the site effect is removed. Z-scoring removes any
   cohort-level age/sex difference along with the site effect.

The disease label **cannot** be a protected covariate. That would require the test
cohort's labels, which spec Section 6.2 forbids. So ComBat, like z-scoring, also
removes the part of each cohort's mean that comes from its PD/control mix. This is
a known limitation, stated up front.

## Decision: pre-declared analysis
- **Implementation:** parametric ComBat written in `neuropd.modeling.harmonization`
  (no new dependency). Batches are the two cohorts in each transfer: ds007526 plus
  one external cohort. It is fitted on the **unlabeled** features of both
  (transductive, as ADR 0011 allows) and applied to the EEG models only.
- **Variants:**
  - `combat`: no covariates;
  - `combat_agesex`: age and sex protected. Missing values are filled with the
    cohort median for age and the cohort mode for sex.
- **Comparators:** `none` and `per_cohort_zscore`, re-run on the same matrices.
- **External cohorts:** ds002778, ds004584, ds003490. The model is fit on all of
  ds007526 and evaluated once per cohort. Nothing is tuned.
- **Models:** all-feature logreg / svm_linear / random_forest, plus relative-power
  logreg (the ADR 0013 model).
- **Primary comparison (descriptive, decided in advance):** all-feature logreg
  external ROC-AUC with 95% bootstrap CI, per cohort.
  - "ComBat helps" means its AUC exceeds `none` in **all three** cohorts.
  - Anything less is reported as no consistent benefit.
  - No significance test: with n=30-133 per cohort, CI overlap is shown instead.
- **Diagnostic:** dataset-identity AUC (ds007526 vs each cohort, grouped 5x5 CV)
  after each harmonizer. This shows whether site separability is actually reduced.

## Alternatives
- **Using the disease label as a covariate:** rejected, because it needs test
  labels.
- **neuroCombat / neuroHarmonize packages:** these would add a dependency. They are
  used only for a one-off numerical cross-check of the in-house implementation,
  which is not committed as a dependency.
- **Training-set-only ComBat fit, applied to new sites:** not possible, because
  ComBat needs each target batch's own statistics.

## Consequences
- Because the harmonizer uses the test cohort's own feature distribution, results
  describe whether the cohorts can be compared, not a deployable model.
- A null result would strengthen the existing conclusion that site effects go
  beyond per-feature location and scale.

## Results (executed 2026-11-08; `docs/combat.md`)

**Implementation check:**
- The in-house ComBat matches `neuroCombat` (one-off, throwaway environment) to
  4e-15 without covariates and 2e-7 with age/sex (the iteration tolerance).
- The first run on real features was degenerate (every AUC 0.500, identity AUC
  1.000). Absolute band power (~1e-11 V²) fell below the absolute variance floors,
  which inflated its cohort gap from 0.45 to 538 SD.
- Fix: features are now divided by their pooled SD before ComBat and rescaled
  after. ComBat is per-feature scale-equivariant, so this is mathematically
  neutral. A regression test covers it.
- Only the corrected run is interpreted.

**Primary comparison** (all-feature logreg external AUC):

| cohort | none | per-cohort z-score | ComBat | ComBat (age/sex) |
| --- | --- | --- | --- | --- |
| ds002778 | 0.720 | 0.751 | 0.760 | 0.747 |
| ds004584 | 0.857 | 0.842 | 0.847 | 0.844 |
| ds003490 | 0.532 | 0.556 | 0.556 | 0.560 |

- **Pre-declared criterion not met for either ComBat variant.** Both are slightly
  better on ds002778 and ds003490 and slightly worse on ds004584.
- Every difference lies well inside the bootstrap CIs (typically ±0.07 to ±0.22).
- Other models show the same pattern. The random forest is hurt by harmonization
  on the two small cohorts (e.g. ds002778 0.767 → 0.653).

**Dataset identity after harmonization:**
- Every harmonizer drives identity AUC from 0.92-0.95 to between 0.00 and 0.05.
- Values far *below* 0.5 come from the grouped cross-validation, not from strong
  site signal. Once cohort means are aligned, each training fold's means are offset
  against its held-out participants, so the classifier predicts backwards.
- The right reading: no linear site signal remains in the per-feature cohort
  means.

## Interpretation
- ComBat removes the first- and second-moment site differences it is designed for,
  as shown by identity separability collapsing.
- Disease transfer does **not** improve consistently. The site effect that limits
  transfer is not a per-feature location/scale offset, which confirms and
  generalises ADR 0011 to three external cohorts and a stronger method.
- Protecting age/sex makes no material difference.
- Conclusion: transfer is limited by differences that per-feature harmonization
  cannot reach, such as recording conditions, populations and topography. It is
  not limited by removable scale offsets.
