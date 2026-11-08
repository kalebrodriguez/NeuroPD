# ADR 0015: Peak-separated aperiodic fit (spectral parameterization), pre-declared

- **Date:** 2026-11-08
- **Status:** accepted (written and committed before any real-data result)

## Context
ADR 0012 added an aperiodic (1/f) exponent and offset from a plain log-log line fit
over 2-40 Hz. Its known weakness is that oscillatory peaks inside the fit range,
especially alpha, pull the line and bias the exponent. Spectral parameterization
(Donoghue et al. 2020, *Nature Neuroscience* 23:1655-1665,
doi:10.1038/s41593-020-00744-x; FOOOF, now `specparam`)
models the aperiodic component and Gaussian peaks together, which removes that
bias. The owner approved this as step 3 (2026-11-08).

## Decision
### Library
- Use **`fooof==1.1.1`**, the latest *stable* release of the algorithm (May 2025).
- Its successor `specparam` has only release candidates on PyPI (2.0.0rc7), which
  are not suitable for a reproducible pipeline.
- `fooof` 1.1 prints a deprecation notice but is fully functional and unchanged.
- The call is isolated in one module (`neuropd.features.specparam_features`), so
  moving to `specparam` 2.0 when it is stable is a one-file change.

### Fit settings (fixed now; `configs/features/specparam.yaml`)
- Frequency range 2-40 Hz, the same as ADR 0012.
- `aperiodic_mode="fixed"` (no knee over 2-40 Hz).
- `peak_width_limits=(1, 8)` Hz: the minimum is twice the 0.5 Hz resolution.
- `max_n_peaks=6`, `min_peak_height=0.1`, `peak_threshold=2.0` (library defaults
  otherwise).

### Unit of fitting
- Fit once per participant and channel, on the **epoch-averaged Welch PSD** (same
  Welch settings as ADR 0006; sessions pooled). Averaging spectra before fitting is
  standard practice and avoids roughly 10^6 noisy per-epoch fits.
- Channel values are averaged within the five scalp regions, giving `sp_exponent`,
  `sp_offset` and `sp_r2` per region.
- For a like-for-like comparison, the ADR 0012 log-log fit is recomputed on the
  **same** averaged spectra (`ll_exponent`, `ll_offset`).

### Pre-declared analyses (descriptive; no new confirmatory claim)
1. **Validation (offline test):** on synthetic spectra with a known exponent and an
   alpha peak, the spectral-parameterization exponent must be within 0.05 of the
   truth, and closer to it than the log-log estimate.
2. **Fit quality:** median and minimum `sp_r2` per cohort.
3. **Group effect:** PD-minus-control difference in the region-mean exponent
   (Cohen's d with 95% bootstrap CI), for both methods in all four cohorts.
   - Reported as sign consistency: is the PD effect in the same direction in
     every cohort?
4. **Transfer:** logreg trained on ds007526 using **aperiodic features only**
   (exponent + offset, 5 regions = 10 features), evaluated once on ds002778,
   ds004584 and ds003490 (95% bootstrap CI). Log-log vs spectral parameterization.
   - "Spectral parameterization helps transfer" means a higher AUC in **all three**
     cohorts.
5. **Swap-in:** the all-feature logreg with the ADR 0012 aperiodic columns replaced
   by the spectral-parameterization ones, per external cohort, compared with the
   current 230-feature model.

## Alternatives
- **`specparam` 2.0 release candidate:** rejected for reproducibility; revisit once
  it is stable.
- **Per-epoch fits:** about 100x the compute and noisier fits, with no gain for the
  participant-level questions asked here.
- **Knee mode:** unnecessary over 2-40 Hz and adds a parameter that is often poorly
  constrained in short recordings.

## Consequences
- Adds one runtime dependency (`fooof`, pure Python on NumPy/SciPy).
- The ADR 0012 log-log features remain in the frozen 230-feature matrix used by
  ADRs 0013/0014, so no earlier result changes. The new features live in a separate
  table (`data/processed/aperiodic_<cohort>.parquet`).

## Results (executed 2026-11-08; `docs/aperiodic_specparam.md`)
- **Validation:** on synthetic spectra with an alpha peak, spectral
  parameterization recovers the exponent within 0.05 and beats the log-log fit
  (offline test, exponents 0.8 / 1.2 / 1.8).
- **Fit quality:** median region-mean R² is 0.985 (ds007526), 0.967 (ds002778),
  0.968 (ds004584) and 0.953 (ds003490). A few individual fits are poor (lowest
  region mean 0.18); they are reported, not excluded, as pre-declared.
- **PD-minus-control exponent effect (Cohen's d):**

  | cohort | log-log | spectral parameterization |
  | --- | --- | --- |
  | ds007526 | 0.04 [-0.35, 0.43] | -0.12 [-0.50, 0.26] |
  | ds002778 | 0.52 [-0.19, 1.30] | 0.38 [-0.37, 1.07] |
  | ds004584 | 0.64 [0.30, 0.99] | 0.52 [0.18, 0.89] |
  | ds003490 | 0.41 [-0.31, 1.14] | 0.07 [-0.66, 0.73] |

- **Aperiodic-only transfer (logreg AUC), log-log → spectral parameterization:**
  - ds002778: 0.676 → 0.707
  - ds004584: 0.697 → 0.656
  - ds003490: 0.524 → 0.575
  - **Pre-declared criterion not met.**
- **Swap-in (all-feature logreg AUC):**
  - ds002778: 0.720 → 0.684
  - ds004584: 0.857 → 0.839
  - ds003490: 0.532 → 0.611
  - All changes are within CIs. The unchanged column reproduces the committed
    230-feature results exactly.

## Interpretation
- **Exponent effect:** in all three external cohorts PD has a steeper log-log
  exponent than controls, but only the ds004584 interval excludes zero.
  Separating peaks **shrinks** the effect everywhere: ds004584 0.64 → 0.52 (still
  clearly non-zero), ds003490 0.41 → 0.07. Part of the apparent "steeper 1/f in PD"
  in a plain line fit therefore comes from oscillatory peaks, consistent with the
  bias ADR 0012 flagged. A peak-independent aperiodic difference remains in the
  largest cohort.
- **Why transfer from ds007526 gains nothing:** the development cohort shows **no**
  exponent difference by either method (d ≈ 0). A model trained there cannot learn
  an aperiodic disease effect, whichever estimator is used.
- **Recommendation:** use spectral parameterization when aperiodic features are
  interpreted physiologically, because it is the less biased estimator. For
  cross-site classification it neither consistently helps nor hurts.
