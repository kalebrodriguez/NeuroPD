# ADR 0004: Line frequency and notch handling for ds002778

- **Date:** 2026-07-23
- **Status:** accepted

## Context
The Milestone 1 audit found that ds002778's `eeg.json` sidecars report an
inconsistent `PowerLineFrequency`: **37/46 recordings say 60 Hz and 9/46 say
50 Hz** (sub-hc8, hc21, hc25, hc31, hc32; sub-pd6/pd13/pd16/pd22 ses-on). The data
were collected in San Diego, USA, where mains power is 60 Hz. Two of the 50-Hz
files (sub-pd6, sub-pd16 ses-on) are also the recordings flagged in
`participants.tsv` as using preprocessed EEGLAB `.mat` data instead of raw.

## Decision
Treat ds002778's electrical line frequency as **60 Hz for all recordings** and,
if a notch filter is used, apply it at **60 Hz** (and harmonics) regardless of the
per-file sidecar value. ds007526 uses **50 Hz** (Israel), applied per dataset.
Encode the line frequency per dataset in configuration rather than trusting the
inconsistent sidecar.

## Alternatives
- Trust each sidecar's `PowerLineFrequency` (rejected: would notch 50 Hz on US
  recordings, missing the real 60 Hz interference and removing valid neural signal
  near 50 Hz).
- Notch both 50 and 60 Hz everywhere (rejected: unnecessarily removes signal;
  not justified by the recording locations).

## Scientific justification
Mains interference occurs at the local supply frequency; San Diego is 60 Hz. The
50-Hz tags are metadata errors, not evidence of 50-Hz interference. Using the
physically correct frequency avoids both under- and over-filtering.

## Consequences
- Preprocessing config carries an explicit per-dataset `line_frequency_hz`
  (ds002778 = 60, ds007526 = 50).
- The sub-pd6/sub-pd16 ON recordings remain flagged for a provenance/sensitivity
  check (already noted in the audit).
