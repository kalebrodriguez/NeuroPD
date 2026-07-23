# Data Dictionary

Definitions of participant-level variables and derived features (spec Section 5.1).
Completed in Milestone 1 (participant metadata) and Milestone 3 (features). Fields
below are transcribed from the datasets' own `participants.json` and are subject to
verification against the real `participants.tsv` during the audit.

## ds007526 participant variables (from participants.json)

| Column | Description | Units / levels |
|---|---|---|
| participant_id | Unique participant identifier | e.g. sub-001 |
| subject_id | Original subject identifier | e.g. HC0001 / PD0001 / PDM001 |
| group | Group assignment | HC = healthy control, PD = Parkinson's disease |
| updrs_part_iii | MDS-UPDRS part III (motor exam) | points |
| updrs_total | MDS-UPDRS total | points |
| moca | Montreal Cognitive Assessment | points |
| age | Age at testing | years |
| sex | Biological sex | F / M |
| disease_duration | Time since PD diagnosis | months |
| ledd | Levodopa Equivalent Daily Dose | mg |
| pigd_score | Postural Instability & Gait Difficulty | derived from MDS-UPDRS |
| td_score | Tremor Dominant score | derived from MDS-UPDRS |
| ctt | Color Trails Test duration | time |

## ds002778 participant variables (from participants.json)

| Column | Description | Units / levels |
|---|---|---|
| participant_id | Unique participant identifier | e.g. sub-hc1 / sub-pd3 |
| age | Age at testing | years |
| gender | Gender identity | F / M |
| hand | Handedness | R / L / A |
| MMSE | Mini-Mental State Examination | points (>24 normal) |
| NAART | North American Adult Reading Test | ~100-point scale |
| disease_duration | Time since diagnosis (PD only) | years |
| rl_deficits | Side/severity of deficits | free text |
| notes | Curation notes | free text |

## Derived features

Populated in Milestone 3 with each feature's name, definition, units, expected
range, missing-value behavior, and reference (spec Section 12.5).
