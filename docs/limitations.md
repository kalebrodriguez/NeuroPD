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

- **Eye condition:** ds007526 rest is eyes-open; ds002778 is unverified. A mismatch
  would be a major confound for alpha-band comparisons.
- **Acquisition:** different systems/montages/channel counts; harmonization is
  imperfect and introduces assumptions.
- **Population/site:** different countries, referral patterns, and line frequency
  (50 vs 60 Hz) may drive dataset-identity effects that rival disease effects.
- **Medication state:** ds002778 PD have ON/OFF sessions; ds007526 medication is
  summarized via LEDD. States are not directly comparable across datasets.

## Scope

- Retrospective analysis of public datasets; not a prospective clinical study.
- No clinical or diagnostic claims are made. Predictive feature importance is not
  evidence of biological causation.
