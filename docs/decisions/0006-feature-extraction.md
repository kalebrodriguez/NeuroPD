# ADR 0006: Interpretable feature extraction and participant aggregation

- **Date:** 2026-07-23
- **Status:** accepted

## Context
Milestone 3 requires interpretable, physiologically motivated features that are
comparable across the two cohorts (spec Section 12). Features must be computed
without leaking participant identity or labels, aggregated to one vector per
participant (Section 12.4), and controlled in number given the small samples
(ds007526 n=144, ds002778 n=31; failure mode Section 28.11).

## Decision
Per (epoch, channel), from a **Welch PSD** (2 s window = 0.5 Hz resolution,
50% overlap, capped at 45 Hz) and the time-domain signal, compute:

- **Spectral (Section 12.1):** absolute, relative, and log band power for
  delta (1-4), theta (4-8), alpha (8-13), beta (13-30) Hz; peak alpha frequency;
  95% spectral edge frequency; theta/alpha and delta/alpha slowing ratios.
- **Complexity (Section 12.2):** normalized spectral entropy, permutation entropy
  (order 3, delay 1), and the three Hjorth parameters (activity, mobility,
  complexity).

That is 21 base features per channel-epoch. Band boundaries and all switches live
in `configs/features/interpretable.yaml` (validated by `FeatureConfig`).

**Spatial harmonization = region (default).** Base features are averaged over the
channels of each of the five scalp regions (frontal, central, temporal, parietal,
occipital) per epoch, then reduced over epochs by **median** (central tendency)
and **IQR** (within-participant variability). This yields
`21 base x 5 regions x 2 stats = 210` features named `{base}__{region}__{stat}`.
A `channel` strategy (per shared channel) is available for the Milestone 6
harmonization comparison.

**Sessions are pooled** per participant (ds002778 on+off) into one row, keeping all
of a participant's data in one place (Section 6.1); medication state remains a
later sensitivity analysis (Section 14.5).

## Alternatives
- **Gamma band:** excluded — the 1-40 Hz band-pass (ADR 0005) attenuates gamma, so
  reported gamma power would be filter-shaped, not physiological.
- **Per-channel features as primary:** rejected for the default — 31 channels x 21 x 2
  = 1302 features is far too many for n=31 external; region aggregation is more
  montage-robust and is retained as the comparison arm instead.
- **Aperiodic (FOOOF) slope/offset:** deferred (`aperiodic: null`) pending a
  reliability check on 2 s / 0.5 Hz-resolution spectra.
- **Sample entropy / Lempel-Ziv:** deferred to avoid redundant complexity features
  (Section 12.2) until the initial set is evaluated.

## Scientific justification
Relative and log power, slowing ratios, peak alpha frequency, and the spectral
edge frequency are established, interpretable markers of the spectral slowing
associated with PD, and (unlike absolute power) are less sensitive to
cross-dataset amplitude/montage scaling. Region aggregation and a fixed, config-
driven feature set keep the count defensible and the later importance maps
readable (region x frequency, Section 15). Robust epoch statistics (median/IQR)
resist artifactual outlier epochs.

## Consequences
- Absolute power is retained but is the least cross-dataset-comparable spectral
  feature; treat it as exploratory/QC and expect regularized models to down-weight it.
- 210 features for n=144 (dev) still exceeds a comfortable ratio; feature selection
  and regularization must happen strictly inside training folds (Section 6.3), and
  the demographics-only and majority baselines bound what the features must beat.
- Peak alpha frequency can be unstable when no clear alpha peak exists; it is
  reported as median-over-epochs and its missingness/variability is tracked.
