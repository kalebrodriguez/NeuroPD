# Limitations

Living document (spec Section 6, Section 22 Milestone 8). Current, honestly stated
limitations — expanded as analyses run.

## Sample size and power

- The external cohort (ds002778) has only 31 participants (15 PD / 16 HC). The
  dataset authors explicitly caution that small-sample PD-vs-HC classification is
  statistically unreliable. NeuroPD therefore frames results as a
  generalization/robustness investigation, reports participant-level uncertainty,
  and treats weak or null transfer as a valid finding.
- The development cohort (ds007526) is larger (144) but imbalanced (~4:1 PD:HC).

## Cross-dataset differences (potential confounders)

- **Eye condition:** RESOLVED — both cohorts are eyes-open resting (ds007526 README;
  ds002778 verified from Jackson et al. 2019). No eye-condition mismatch. (ds002778's
  eye condition is absent from its BIDS sidecars — a provenance caveat.)
- **Acquisition:** different systems and sampling rates (ds002778 512 Hz BioSemi,
  32 scalp channels; ds007526 250 Hz, 60 scalp channels). Harmonization uses the
  **31 shared 10-20 channels** and/or region-level aggregation and resampling to a
  common rate; this is imperfect and introduces assumptions.
- **Age/sex confound (quantified):** in ds007526 PD are older than HC (66.1 vs 60.8 y)
  and more male (62% vs 46%); ds002778 is age/sex-balanced. Requires a demographics-only
  baseline and age/sex-adjusted sensitivity analyses.
- **Population/site & line frequency:** different countries and mains frequency (60 Hz
  US vs 50 Hz Israel) may drive dataset-identity effects that rival disease effects.
  ds002778 sidecars also mislabel line frequency on 9/46 recordings (handled per ADR 0004).
- **Medication state:** ds002778 PD have ON/OFF sessions; ds007526 medication is
  summarized via LEDD. States are not directly comparable across datasets. Two ds002778
  ON recordings (sub-pd6, sub-pd16) used preprocessed rather than raw data.

## Scope

- Retrospective analysis of public datasets; not a prospective clinical study.
- No clinical or diagnostic claims are made. Predictive feature importance is not
  evidence of biological causation.
