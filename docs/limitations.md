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

## Quality-control exclusions (Milestone 3)

- Full-cohort preprocessing at the predeclared 150 µV threshold (ADR 0005) excluded
  **11/144 ds007526 recordings, of which 10 are PD** (sub-083, 107, 111, 112, 120,
  123, 124, 125, 129, 130) and 1 HC (sub-025, borderline at 19 clean epochs). The
  excluded PD recordings are genuinely high-amplitude — post-filter median
  worst-channel peak-to-peak ≈ 325-388 µV with **every** epoch exceeding 150 µV,
  versus ≈ 68 µV for a typical retained recording — so this is real artifact, not a
  units/scaling bug. ds002778 excluded 1/31 (HC sub-hc25, 9 clean epochs).
- **This exclusion is PD-concentrated**, so the retained ds007526 cohort (27 HC /
  106 PD) may be biased toward less artifact-prone (possibly less severe or less
  tremor-dominant) PD participants. The threshold was **not** loosened post hoc to
  retain them (that would be outcome-driven tuning). A lenient-threshold and/or
  ICA-based **sensitivity analysis is proposed** (Section 14.5) to quantify how much
  this exclusion affects results.

## Demographic confounding — empirically confirmed (Milestone 4)

- Internal baselines on ds007526 show a **demographics-only (age + sex) model
  reaching balanced accuracy ≈ 0.65, exceeding every EEG model (≈ 0.56-0.59)**;
  EEG models rank somewhat better on ROC-AUC (random forest ≈ 0.76 vs demographics
  ≈ 0.69). Because ds007526 PD are older and more male than HC, within-cohort
  group separation is partly driven by demographics, not brain physiology. EEG
  performance must therefore be read **relative to** the demographics baseline, and
  age/sex-adjusted sensitivity analyses (Section 6.4) are required before attributing
  separation to EEG. This does not show EEG is uninformative — it bounds how much of
  the apparent signal is confounded.
- The EEG baselines also show high sensitivity (~0.8) with low specificity (~0.33):
  they lean toward the PD majority class despite balanced class weighting.

## Feature count vs. sample size

- The default region-level matrix has **210 features** (21 base × 5 regions × 2
  stats) for n=133 (development) and n=30 (external). This exceeds a comfortable
  feature-to-participant ratio (failure mode Section 28.11), so all feature selection,
  scaling, and dimensionality reduction must be fitted strictly inside training folds
  (Section 6.3), and simple/regularized baselines plus a demographics-only baseline
  bound what the EEG features must beat. Absolute band power is retained but is the
  least cross-dataset-comparable spectral feature.

## Scope

- Retrospective analysis of public datasets; not a prospective clinical study.
- No clinical or diagnostic claims are made. Predictive feature importance is not
  evidence of biological causation.
