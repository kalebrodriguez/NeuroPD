# Feature Dictionary

Interpretable, participant-level EEG features (spec Section 12). Definitions,
units, and decisions are fixed in `configs/features/interpretable.yaml` and
`docs/decisions/0006-feature-extraction.md`. Implementations and synthetic-signal
tests are in `src/neuropd/features/` and `tests/test_features.py`.

## Naming scheme

Participant feature columns are `{base}__{unit}__{stat}`:

- **base** — one of the 21 base features below.
- **unit** — scalp region (`frontal`, `central`, `temporal`, `parietal`,
  `occipital`) under the default `region` strategy, or a shared channel name under
  the `channel` strategy (Section 11).
- **stat** — epoch-aggregation statistic: `median` (central tendency) or `iqr`
  (within-participant variability across epochs, Section 12.4).

Default matrix size: `21 base × 5 regions × 2 stats = 210` features, one row per
participant. Example: `rel_power_alpha__occipital__median`.

Non-feature metadata columns (kept physically separate from features so they can
never leak into the model, Section 6.3): `participant_id`, `dataset`, `group`,
`n_sessions`, `n_epochs`.

## Base features (per epoch, per channel)

All computed from a Welch PSD (2 s window → 0.5 Hz resolution, 50% overlap,
≤ 45 Hz) or the time-domain signal. Input signals are in volts.

| Base feature | Definition | Unit | Interpretation |
|---|---|---|---|
| `abs_power_{delta,theta,alpha,beta}` | ∫ PSD over the band | V²  | Band power (amplitude-sensitive; least cross-dataset comparable) |
| `rel_power_{band}` | band power ÷ Σ band powers | fraction (0–1) | Share of spectrum in the band; robust to scaling |
| `log_power_{band}` | log₁₀(absolute band power) | log V² | Variance-stabilized band power |
| `paf` | frequency of max PSD in 8–13 Hz | Hz | Peak alpha frequency; **lower with PD spectral slowing** |
| `sef` | frequency below which 95% of 0–45 Hz power lies | Hz | Spectral edge; **lower with slowing** |
| `theta_alpha_ratio` | abs theta ÷ abs alpha | ratio | Slowing index |
| `delta_alpha_ratio` | abs delta ÷ abs alpha | ratio | Slowing index |
| `spectral_entropy` | normalized Shannon entropy of the PSD | 0–1 | Spectral flatness (1 = white, 0 = single tone) |
| `perm_entropy` | Bandt–Pompe permutation entropy (order 3, delay 1) | 0–1 | Ordinal-pattern regularity (1 = noise, 0 = monotone) |
| `hjorth_activity` | variance of the signal | V² | Signal power |
| `hjorth_mobility` | √(var(dx)/var(x)) | dimensionless | ∝ mean frequency |
| `hjorth_complexity` | mobility(dx)/mobility(x) | dimensionless | Departure from a pure sine (=1 for a sinusoid) |

Bands (Hz, from config): delta 1–4, theta 4–8, alpha 8–13, beta 13–30. Gamma is
disabled (attenuated by the 1–40 Hz preprocessing band-pass; ADR 0006).

## Missing-value behavior

Feature functions return `NaN` (never a silent 0 or fabricated value) when a
quantity is undefined — e.g. a band with fewer than two PSD bins, a log of
non-positive power, a ratio with a zero denominator, or Hjorth terms of a constant
signal. NaN counts per matrix are recorded in
`data/metadata/feature_extraction_info.json`.
