# ADR 0005: Conservative preprocessing pipeline

- **Date:** 2026-07-23
- **Status:** accepted

## Context
Milestone 2 requires a conservative, reproducible preprocessing pipeline for
cross-dataset resting-state EEG. Parameters were chosen after inspecting the real
recordings (Milestone 1 audit) and must harmonize ds002778 (BioSemi, 512 Hz, 32
scalp) and ds007526 (250 Hz, 60 scalp), which differ in montage and sampling rate.

## Decision
Conservative profile (`configs/preprocessing/conservative.yaml`), applied in this
order per recording:
1. Normalize channel names; **restrict to the 31 shared 10-20 channels** (ADR/audit).
2. Set a `standard_1005` montage.
3. **Notch** at the per-dataset line frequency (ds002778 = 60 Hz, ds007526 = 50 Hz; ADR 0004).
4. **Band-pass 1-40 Hz** (remove drift; stay below mains/EMG; cover delta..beta).
5. **Resample to 250 Hz** (ds007526 native; downsample ds002778 from 512 Hz).
6. **Average reference** (matches Jackson et al. 2019 for ds002778).
7. **Fixed-length 2 s non-overlapping epochs**.
8. **Reject** epochs with peak-to-peak > 150 µV or < 1 µV (flat).
9. Exclude a recording only if < 60 s or < 20 clean epochs (predeclared).

No ICA in the conservative profile (avoids subjective, hard-to-reproduce component
choices); a wider-band, more-lenient `sensitivity` profile exists for robustness
checks (Section 14.5).

## Alternatives
- Trust per-file line frequency (rejected — ADR 0004).
- Keep native sampling rates (rejected — features must be comparable across cohorts).
- CSD/REST reference (deferred — average reference is transparent and matches the
  ds002778 source analysis; CSD can be a sensitivity analysis).
- Overlapping epochs (used in the sensitivity profile, not the conservative one).

## Scientific justification
Average reference, a shared channel set, a common sampling rate, and identical
filtering make spectral/complexity features comparable across datasets. Amplitude-
based rejection is fully reproducible. Fixed-length epochs give many within-
participant samples while participant-level aggregation preserves independence.

## Consequences
- The 40 Hz low-pass makes the notch largely redundant in the conservative profile,
  but the notch is retained (correct per ADR 0004 and matters if the band is widened).
- Restricting to 31 channels discards ds007526's higher density (revisit via
  region-level aggregation if useful).
- **Observed:** ds002778 shows higher epoch rejection (~45-57% for some HC) than
  ds007526 (~2-6%) at 150 µV, reflecting larger-amplitude/less-cleaned BioSemi data;
  all audited recordings still retain well above 20 clean epochs. Revisit the
  threshold or add ICA as a sensitivity analysis if needed.
