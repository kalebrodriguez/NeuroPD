# ADR 0015: Peak-separated aperiodic fit (spectral parameterization), pre-declared

- **Date:** 2026-11-08
- **Status:** accepted (written and committed before any real-data result)

## Context
ADR 0012 added an aperiodic (1/f) exponent and offset from a plain log-log line fit
over 2-40 Hz. Its known weakness is that oscillatory peaks inside the fit range,
especially alpha, pull the line and bias the exponent. Spectral parameterization
(Donoghue et al. 2020, *Nature Neuroscience* 23:1655-1665; FOOOF, now `specparam`)
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
