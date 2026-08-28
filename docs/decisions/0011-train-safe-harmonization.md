# ADR 0011: Train-safe cross-dataset feature harmonization

- **Date:** 2026-08-28
- **Status:** accepted

## Context
The project's central result is that the shared EEG feature space is dominated by
**site/acquisition** effects: dataset identity is predicted at AUC ≈ 0.95, far
above disease (≈ 0.72 internal, ≈ 0.65 external), and disease feature-importance
does not agree across cohorts. The natural follow-up (spec Section 27, "domain
adaptation using training-safe methods"): if per-cohort location/scale differences
are removed, does the disease signal transfer better?

## Decision
Add an optional **per-cohort standardization** step for the external-transfer
experiment (`neuropd.modeling.harmonization`, `scripts/evaluate_external.py
--harmonize {per_cohort_zscore,per_cohort_robust}`). Each cohort's feature matrix
is standardized using **its own** feature statistics (z-score, or median/IQR for
the robust variant) before the EEG models are fit/applied. It is applied to the
EEG-feature models only; the demographics and majority baselines are unchanged,
and the internal cross-validated reference is left unharmonized.

The frozen baseline report (`docs/external_transfer.md`, `--harmonize none`)
remains the primary result; harmonized variants are written to separate files
(`docs/external_transfer_<method>.md`).

## Alternatives
- **ComBat / neuroCombat** (empirical-Bayes batch correction): the standard tool,
  but with a single batch per split (train = one site, test = the other) it reduces
  to per-batch location/scale correction while adding estimation complexity and a
  dependency. Per-cohort standardization is the transparent core of the same idea.
- **Model-internal `StandardScaler` only** (already present): fits on train and
  applies train statistics to test, so it *cannot* correct a between-cohort shift.
- Fitting a scaler on pooled train+test features (rejected: entangles the cohorts
  and is harder to reason about than independent per-cohort standardization).

## Scientific justification & leakage
Standardizing the external cohort by its own statistics uses only its **unlabeled**
feature distribution — never its labels — which spec Section 6.2 explicitly permits
and documents. It does not tune the model on the external cohort. This isolates the
question "is the residual, shape-based disease signal cohort-invariant once global
scale/shift is removed?" — consistent with the sensitivity finding that *relative*
(normalized) band power already transfers better than absolute power.

## Consequences
- Harmonization can only remove **global** per-feature location/scale differences,
  not higher-order distributional or topographic site effects; a null improvement is
  itself informative.
- Because standardization uses the test cohort's own distribution, results are
  reported as a transductive domain-adaptation analysis, not a deployable model.
