# ADR 0021: Is the QC sensitivity of transfer carried by amplitude-sensitive features? (pre-declared)

- **Date:** 2026-11-24
- **Status:** accepted (written and committed before any per-family lenient-threshold result was computed)

## Context
ADR 0020 found that all-feature transfer degrades as the artifact threshold
loosens, while relative power is steadier:
- all-feature, ds002778: 0.720 → 0.588 → 0.425 at 150 / 200 / 400 µV;
- relative power, ds004584: 0.733 → 0.711 → 0.682.

The interpretation offered was that high-amplitude epochs add site-specific
artifact which amplitude-sensitive features absorb. That reading was not tested.
This ADR tests it on the feature matrices ADR 0020 already produced. No new
preprocessing is needed. The owner asked to continue (2026-11-24).

## Decision: pre-declared analysis
**Families** (`neuropd.features.families`):
- **Amplitude-sensitive (A):** absolute power and log power. Both scale with
  signal amplitude.
- **Amplitude-invariant (N):** relative power and slowing (PAF, SEF and band
  ratios). Both are normalized within each spectrum.
- **Complexity:** mixed. Hjorth activity is a variance, but the entropies are
  scale-free. It is reported descriptively and not tested.

**Measure.** For each family, train a logistic regression on ds007526 and
evaluate it once on each external cohort (ds002778, ds004584, ds003490). Do this
at 150, 200 and 400 µV, with the same features, model, seed and bootstrap as
ADR 0020. A family's **degradation** is its mean over the three cohorts of
AUC(150 µV) − AUC(400 µV).

**Pre-declared prediction (H5).** Every amplitude-sensitive family degrades more
than every amplitude-invariant family:
min(degradation of absolute, log) > max(degradation of relative, slowing).
H5 is supported if this holds, and not supported otherwise.

**Descriptive:**
- per-family AUCs at each threshold;
- the 200 µV values;
- per-family site identity AUC (ds007526 vs each cohort) at 150 and 400 µV, to
  see whether amplitude-sensitive families become more site-identifying.

**Disclosure.** Relative power on ds004584 and ds003490 at all three thresholds is
already known from ADR 0020: the ds004584 drop is 0.051, and ds003490 rises by
0.046. Its ds002778 value, and every other family's values, have not been
computed.

## Consequences
- If H5 is supported, the ADR 0020 explanation is upgraded from a plausible
  reading to a tested result. That supports normalized features plus strict
  artifact rejection for cross-site EEG work.
- If not, the manuscript's sentence attributing the degradation to
  amplitude-sensitive features must be weakened or removed.

## Results (executed 2026-11-24; `docs/qc_by_family.md`)

Mean degradation, AUC(150 µV) − AUC(400 µV), over the three external cohorts:

| family | class | degradation |
| --- | --- | --- |
| relative power | amplitude-invariant | **+0.107** |
| log power | amplitude-sensitive | +0.062 |
| complexity | mixed | +0.060 |
| slowing | amplitude-invariant | +0.006 |
| absolute power | amplitude-sensitive | **−0.024** |

- **Pre-declared verdict: H5 not supported.** The minimum amplitude-sensitive
  degradation (−0.024, absolute power) is below the maximum amplitude-invariant one
  (+0.107, relative power). The ordering is roughly the reverse of the prediction.
- **Consistency check:** relative power on ds002778 at 150 µV is 0.867. That is the
  exploratory value from ADR 0010.
- **Descriptive:**
  - Relative power's degradation is driven by ds002778 (0.867 → 0.717 → 0.550).
  - Site identity rises from 150 to 400 µV for every family in every cohort.

## Interpretation
- **The ADR 0020 explanation was wrong.** Loosening artifact rejection does not
  mainly hurt amplitude-sensitive features. Relative power, a normalized feature,
  loses the most, mostly on ds002778. "Relative power is steadier" was true only
  for ds004584.
- **What does hold:** looser QC makes every feature family more site-identifying.
  The mechanism is not identified here. Artifacts plausibly change spectral shape
  as well as amplitude, so normalization does not protect against them. That is a
  hypothesis, not a result.
- **Practical reading:** strict artifact rejection matters for cross-site transfer
  whichever features are used. Normalized features are not a substitute for it.
- **Corrections made:** the manuscript (Section 3.4), the report, `limitations.md`
  and an addendum to ADR 0020 no longer attribute the degradation to
  amplitude-sensitive features.
