# ADR 0016: Leave-one-site-out multi-site training (pre-declared)

- **Date:** 2026-11-08
- **Status:** accepted (written and committed before any multi-site result was computed)

## Context
Every transfer result so far trains on a **single** site (ds007526):

- Disease signal transfers clearly to ds004584 (AUC 0.857 all-feature, 0.733
  pre-registered relative power).
- It transfers modestly to ds002778 (0.720) and not detectably to ds003490
  (0.532).
- Site stays far easier to predict than disease (AUC 0.92-0.95).
- Per-feature harmonization (ADRs 0011, 0014) did not help.

The standard remaining remedy for site effects is to **train on several sites**,
so that the model cannot rely on any one site's quirks. With four cohorts this can
be tested by leave-one-site-out (LOSO) evaluation without new data (owner: "move to
the next stage", 2026-11-08). It extends the analysis and does not change the
central research question.

## Decision: frozen analysis plan
- **Sites:** ds007526 (Tel Aviv), ds002778 (UC San Diego), ds004584 (Iowa) and
  ds003490 (New Mexico). Each site uses its existing 230-feature region-level
  participant matrix (ADR 0006/0012), unchanged.
- **LOSO folds:** each site is held out once. The model is fit on the other three
  sites pooled and evaluated **once** on the held-out site. Nothing is tuned on the
  held-out site.
- Participant ids are prefixed with their site, and a disjointness check asserts
  that no held-out participant is in training.
- **Arms:**
  - **A, single-site:** fit on ds007526 only. This is the existing reference,
    recomputed in the same script. It applies to the three non-ds007526 held-out
    sites.
  - **B, multi-site pooled:** fit on the three training sites pooled, features as
    they are.
  - **C, multi-site per-site standardized:** each site (training and held-out) is
    z-scored with its own unlabeled feature statistics before pooling. This is the
    train-safe ADR 0011 step, applied per site.
- **Models:** all-feature logreg (**primary**), relative-power logreg, svm_linear,
  random_forest, and a demographics-only (age/sex) baseline for arm B. All use the
  existing `make_estimator` pipelines, with class weights balanced on the pooled
  training set.
- **Primary comparison:** all-feature logreg external ROC-AUC with a 95%
  participant-level bootstrap CI (2,000 resamples, seed 20240517), per held-out
  site.
  - **H2, "multi-site training helps":** arm B *or* arm C has a higher AUC than
    arm A in **all three** of ds002778, ds004584 and ds003490.
  - Each arm is also reported against arm A on its own.
  - No significance test is run; CI overlap is shown instead.
- **Secondary (descriptive):**
  - held-out ds007526 performance for arms B and C, with no single-site
    comparator;
  - pooled-over-folds summary;
  - dataset-identity AUC among the three training sites in each fold (grouped
    5x5 CV), to see how site-dominated the pooled training data are.

## Known limitations (stated in advance)
- **Disease prevalence differs by site:** about 80% PD in ds007526, 50% in
  ds002778, 67% in ds004584 and 64% in ds003490. So site and label are partly
  confounded in pooled training. Arm C removes each site's mean, including its
  disease-mix contribution, as noted in ADRs 0011 and 0014.
- **ds007526 and ds004584 dominate pooled training** (133 participants each,
  against 30 and 33).
- **ds004584 and ds003490 share an author** (J. F. Cavanagh), though they come
  from different sites. A fold that trains on one and tests on the other is
  therefore not fully independent.

## Alternatives
- **Weighting sites equally in training:** that adds a tuning choice. Class
  balancing alone is the existing convention.
- **Pooling all four sites with cross-validation:** this mixes sites across folds
  and measures within-site rather than cross-site generalization. Rejected.
- **Domain-adversarial or deep models:** out of scope for an interpretable,
  low-complexity pipeline (spec Section 13.4).

## Consequences
- If multi-site training helps consistently, the conclusion becomes that disease
  signal is learnable across sites given site diversity in training.
- If it does not, the site problem is not solved by pooling either. That would be
  informative, consistent with ADRs 0011 and 0014.
- Research tool only: group-level estimates, not a diagnostic test.

## Results (executed 2026-11-08; `docs/multisite.md`)
All-feature logreg external ROC-AUC:

| held-out site | A single-site | B multi-site pooled | C multi-site per-site z |
| --- | --- | --- | --- |
| ds007526 (n=133) | – | 0.630 [0.495, 0.756] | 0.631 [0.503, 0.754] |
| ds002778 (n=30) | 0.720 [0.520, 0.890] | 0.684 [0.472, 0.862] | 0.813 [0.636, 0.946] |
| ds004584 (n=133) | 0.857 [0.788, 0.916] | 0.841 [0.768, 0.907] | 0.840 [0.767, 0.905] |
| ds003490 (n=33) | 0.532 [0.308, 0.739] | 0.619 [0.388, 0.817] | 0.663 [0.435, 0.857] |

- **H2 is not supported.** Neither B nor C beats A in all three comparable sites;
  both are 0.016-0.017 below A on ds004584, well inside the CI.
- Arm A reproduces the earlier single-site results exactly (0.720 / 0.857 / 0.532).
- **Arm C (multi-site with per-site standardization) is better than A on the two
  small sites in most models:**
  - ds002778: logreg 0.720 → 0.813, svm 0.680 → 0.840, random forest
    0.767 → 0.838;
  - ds003490: logreg 0.532 → 0.663, svm 0.544 → 0.631.
  - The relative-power logreg does **not** follow this pattern (ds002778
    0.867 → 0.778).
- Arm B (pooled, unstandardized) gives mixed changes.
- Held-out ds007526 is predicted only modestly from the other three sites (AUC
  about 0.63), below its own internal CV (0.72).
- The demographics-only model is at or below chance in every fold (0.39-0.49).
- Site identity among the training sites is 0.75-0.88 one-vs-rest AUC on raw
  features. Per-site z-scoring drives it to ~0, the same CV artifact as ADR 0014
  once site means are aligned.

## Interpretation
- Pooling sites as they are does not help. With per-site standardization, multi-site
  training tends to improve transfer to the small held-out sites, by about 0.09-0.16
  AUC. That contrasts with ADRs 0011 and 0014, where the same standardization did
  nothing for a single-site model. The likely reason is site diversity in training:
  once each site is centred, the model must find disease structure that is shared
  across sites rather than one site's idiosyncrasies.
- This is **directional, not confirmed**. The pre-declared all-three criterion
  fails narrowly on ds004584, and the gains on the small sites have CIs that
  overlap arm A's. A new site evaluated under this exact arm-C recipe would be the
  confirmatory test.
- ds007526 being hard to predict from the other sites (0.63) shows that transfer is
  asymmetric: the largest, most imbalanced, Tel Aviv cohort differs from the US
  cohorts in ways the others do not cover.
