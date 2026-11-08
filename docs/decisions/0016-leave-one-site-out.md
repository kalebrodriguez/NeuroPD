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
