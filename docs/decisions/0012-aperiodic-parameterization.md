# ADR 0012: Aperiodic (1/f) spectral feature

- **Date:** 2026-08-28
- **Status:** accepted

## Context
"Spectral slowing" in Parkinson's disease is usually summarized with band-power
ratios (e.g. theta/alpha), but part of that apparent slowing can reflect the
**aperiodic (1/f)** background of the spectrum rather than oscillatory changes
(spec Sections 12.1, 27). Separating the aperiodic component gives a more
interpretable, physiologically distinct feature.

## Decision
Add an aperiodic feature pair — **`aperiodic_exponent`** (1/f slope magnitude) and
**`aperiodic_offset`** (broadband level) — estimated by a robust **log-log linear
fit** of `log10(PSD)` vs `log10(freq)` over a configurable range
(`aperiodic_fmin`–`aperiodic_fmax`, default 2–40 Hz), implemented in
`neuropd.features.spectral.aperiodic_fit` and enabled in
`configs/features/interpretable.yaml`. The features flow through the existing
region/channel + robust epoch aggregation like every other base feature.

## Alternatives
- **FOOOF / `specparam`** full spectral parameterization (separately models
  periodic peaks + aperiodic component). More principled, but adds a dependency and
  per-spectrum fitting cost/failure modes. Deferred as a future refinement; the fit
  range here (2–40 Hz, above the 1 Hz high-pass edge) reduces peak influence.
- Report only band-ratio "slowing" (rejected: conflates aperiodic and oscillatory
  contributions, which this feature disentangles).

## Scientific justification
On a log-log axis a `1/f^a` spectrum is a straight line with slope `-a`; the fitted
exponent recovers `a` (validated on synthetic `1/f^a` spectra to within numerical
tolerance). The exponent indexes the excitation/inhibition-related broadband tilt;
the offset indexes overall power. Both are interpretable and montage-transferable.

## Consequences
- Adds two base features per spatial unit (per region or per channel), increasing
  the participant feature-matrix width; results docs are regenerated accordingly.
- The log-log fit is a lightweight approximation; when peaks are strong within the
  fit range the exponent is slightly biased — acceptable for a screening feature and
  flagged for a possible FOOOF-based follow-up.
