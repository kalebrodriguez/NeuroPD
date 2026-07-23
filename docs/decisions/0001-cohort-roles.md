# ADR 0001: Development vs external-validation cohort assignment

- **Date:** 2026-07-23
- **Status:** accepted

## Context
Two PD resting-state EEG datasets are in scope: ds007526 (144 participants) and
ds002778 (31 participants). The study design requires one development cohort for
model building/internal cross-validation and one independent cohort held out for
frozen external transfer evaluation (spec Section 6.2).

## Decision
Use **ds007526 as the development cohort** and **ds002778 as the external-validation
cohort**. Bidirectional transfer (train on ds002778, test on ds007526) is an
optional later, separate experiment.

## Alternatives
- ds002778 as development, ds007526 as external (rejected as primary: ds002778 is
  small and its authors caution against classification on it).
- Pooling both datasets into one split (rejected: destroys the external-validation
  design and hides dataset-shift effects).

## Scientific justification
- External validity is the central research question; a held-out independent cohort
  is required.
- The larger, more balanced-by-count development set (ds007526) supports more
  stable internal cross-validation; the smaller ds002778 is well suited to a single
  frozen transfer check.
- Respects the ds002778 authors' caution by not resting primary model development
  on that small cohort.

## Consequences
- Class imbalance in ds007526 (~4:1 PD:HC) must be handled with imbalance-robust
  metrics and training-fold-only weighting.
- Cross-dataset acquisition/condition differences must be harmonized and reported
  as part of the generalization-gap analysis.
