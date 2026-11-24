# ADR 0020: Sensitivity of the main results to the quality-control threshold (pre-declared)

- **Date:** 2026-11-24
- **Status:** accepted (written and committed before any lenient-threshold result was computed)

## Context
- The conservative pipeline (ADR 0005) rejects 2 s epochs whose peak-to-peak
  amplitude exceeds 150 µV. It excludes a recording that keeps fewer than 20 clean
  epochs.
- The resulting exclusions are uneven:
  - In ds007526, 10 of 11 excluded recordings are PD. Their worst-channel
    peak-to-peak amplitude is about 325–388 µV (`docs/limitations.md`).
  - In ds003490, losses hit controls hardest.
- `docs/limitations.md` has proposed a lenient-threshold sensitivity analysis since
  Milestone 3. It was never run.
- The question matters for two reasons:
  - The excluded PD participants may differ systematically (more artifact-prone,
    possibly more severe).
  - ADR 0018 found the within-PD slowing–cognition association concentrated in a
    tail of participants with marked slowing.
- The owner asked to continue with the next milestone (2026-11-24). No new data
  are needed; the raw data are already present.

## Decision: pre-declared analysis
**Arms.** Re-preprocess all four cohorts at two lenient rejection thresholds. Every
other setting stays exactly as in the conservative profile (filters, notch,
resampling, reference, epoching, flat-epoch rule, the 60 s and 20-epoch exclusion
rules, adapters, features):
- **200 µV**, the rejection value of the `sensitivity` profile defined in
  Milestone 2 (`configs/preprocessing/sensitivity.yaml`);
- **400 µV**, chosen to retain the documented high-amplitude ds007526 exclusions
  (325–388 µV). Disclosure: this value was chosen with knowledge of those
  recordings' amplitudes, but with no knowledge of any outcome at this threshold.

Outputs go to `data/processed_qc200/` and `data/processed_qc400/`. The primary
`data/processed/` data, QC tables and feature provenance are not modified.

**Measures.** Each is computed exactly as in its original ADR:
1. **ADR 0013 transfer:** relative-power logistic regression trained on ds007526,
   evaluated once on ds004584 and on ds003490 (ROC-AUC with a participant-level
   bootstrap CI).
2. **Site identity versus disease transfer:** for each external cohort (ds002778,
   ds004584, ds003490), compare
   - the ds007526-vs-cohort identity AUC (grouped CV, as in ADR 0014), with
   - the all-feature logistic-regression transfer AUC.
3. **ADR 0017 within-PD association:** the global theta/alpha ratio against MoCA,
   age-partialled Spearman, at ds007526 and ds004584.
4. **Descriptive:**
   - participants retained per cohort and group;
   - the number of previously excluded participants now retained;
   - all-feature transfer AUCs.

**Pre-declared rule.** The main results are called **robust to the QC threshold**
if, at **both** lenient thresholds:
- (a) the ADR 0013 verdicts are unchanged: CI lower bound > 0.50 at ds004584
  (confirmed), and not at ds003490 (not confirmed);
- (b) site identity AUC exceeds the all-feature disease transfer AUC in each of
  the three external cohorts;
- (c) the ADR 0017 verdict is unchanged: the global theta/alpha ratio is negative
  with p < 0.025 at both ds007526 and ds004584.

A change at either threshold is reported as a limitation of the conservative-QC
results, not hidden.

## Consequences
- If the results are robust, the PD-concentrated exclusions are shown not to
  drive the main conclusions. This is an existing open limitation.
- If they are not, the paper must say which result depends on artifact-based
  exclusion and in which direction.
- The primary (150 µV) analysis remains the pre-registered one. This ADR does not
  replace it.
