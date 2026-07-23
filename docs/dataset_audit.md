# Dataset Audit

This document will hold the **versioned dataset-audit report** required before the
main analysis pipeline is written (spec Section 5.1). It is completed in
Milestone 1 from the real files. The table below records only metadata that has
already been **verified** (OpenNeuro GraphQL API + each dataset's
`participants.tsv`/`README`, retrieved 2026-07-23). Scientific parameters marked
"to verify" must be confirmed from real recording sidecars and are **not** assumed.

## Verified summary

| Field | ds007526 (development) | ds002778 (external) |
|---|---|---|
| Name | PD-EEG: Resting-State & Walking EEG in PD | UCSD Resting State EEG in PD |
| Snapshot | v1.0.2 (2026-06-08) | v1.0.5 (2021-12-10) |
| DOI | 10.18112/openneuro.ds007526.v1.0.2 | 10.18112/openneuro.ds002778.v1.0.5 |
| License | CC0 | CC0 |
| Download size | 4,578,751,379 B (~4.27 GiB) | 571,470,906 B (~545 MiB) |
| Participants | 144 (116 PD / 28 HC) | 31 (15 PD / 16 HC) |
| Tasks | rest, walk | rest |
| Rest condition | sitting, eyes-open, ~4 min | **to verify (eye condition unknown)** |
| Sessions | none | PD: ses-off + ses-on; HC: ses-hc |
| Acquisition | 64-ch EGI Geodesic GES 400, 10-20 | to verify |
| Clinical data | UPDRS-III/total, MoCA, LEDD, PIGD, TD, CTT, disease duration | age, gender, hand, MMSE, NAART, disease duration, side |
| Citation request | contact authors (Tel Aviv Sourasky) | email arockhil@uoregon.edu before publication; cite Jackson 2019 / Swann 2015 / George 2013 |

## Known cross-dataset concerns (to resolve in Milestone 1+)

1. **Eye condition mismatch (high impact).** ds007526 rest is eyes-open; ds002778
   is unverified. Eyes-open vs eyes-closed strongly affects alpha power. **First
   Milestone 1 task: verify ds002778's eye condition; if it differs, document and
   propose defensible handling before any external analysis.**
2. **Montage/system differences.** Different systems and channel counts require
   harmonization (exact shared-channel subset and region-level aggregation).
3. **Class imbalance.** ds007526 is ~4:1 PD:HC; ds002778 is near-balanced. Use
   imbalance-robust metrics and training-fold-only weighting.
4. **Medication sessions (ds002778).** PD have ON+OFF; isolation must keep both
   sessions of a participant together.
5. **Author caution (ds002778).** The dataset authors advise against small-sample
   PD-vs-HC classification; NeuroPD is framed as a generalization/robustness study.

## To be completed in Milestone 1

Per-recording verification (from real sidecars): sampling frequencies, exact
channel names/counts and the common channel set, reference scheme, recording
durations, line frequency, missing/corrupted files, and confounder tabulation
(age/sex distributions per group and dataset). Download sizes and licenses above
are already confirmed; nothing is downloaded until approved.
