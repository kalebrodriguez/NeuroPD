# ADR 0013: Confirmatory evaluation on two new held-out cohorts (pre-registration)

- **Date:** 2026-11-08
- **Status:** accepted (pre-registered; committed **before** either cohort's EEG was
  downloaded into the project environment)

## Context
The strongest transfer result so far is that **relative band power** features
trained on ds007526 reached external ROC-AUC 0.867 on ds002778 (ADR 0010,
`docs/sensitivity.md`). That number is exploratory, not confirmatory:
- it was one of five feature families compared *after* the external cohort's
  results were visible (a forking-paths risk);
- the external cohort is small (n=30), so the interval is wide.

The only clean way to test it is on cohorts the analysis has never touched, with
the test fixed in advance. The owner approved adding two OpenNeuro cohorts
(2026-11-08), one at a time:

| cohort | site | participants | rest condition | system |
| --- | --- | --- | --- | --- |
| **ds004584** v1.0.0 | Univ. of Iowa | 100 PD, 49 control | eyes open, seated, ~2-4.7 min | 63-ch BrainVision, 500 Hz, ref Pz, 60 Hz mains |
| **ds003490** v1.1.0 | Univ. of New Mexico | 25 PD (ON + OFF sessions), 25 control | 1 min eyes open within a rest + oddball recording | 64-ch BrainVision actiCHamp, 500 Hz, ref CPz, 60 Hz mains |

Both are CC0. Both are independent of ds007526 (Tel Aviv) and ds002778 (UC San
Diego). They come from different sites but share an author (J. F. Cavanagh), so
they are not fully independent of *each other*. Each is analysed and reported
separately.

## Decision: frozen analysis plan

### Fixed before seeing any data
- **Training:** fit on the **full ds007526** cohort only, exactly as in ADRs
  0008/0010. ds002778 is **not** added to training, and nothing is tuned on either
  new cohort.
- **Pipeline:** the conservative preprocessing profile (ADR 0005), the
  `interpretable.yaml` feature config (region spatial, median + IQR aggregation;
  ADR 0006), and the 31-channel `harmonization.yaml` set, unchanged.
- **Model:** `logreg` baseline (`make_estimator("logreg", seed=20240517)`).
- **Primary hypothesis (H1), tested separately per cohort:** logreg trained on the
  **relative band power** family (columns starting `rel_power_`, the same
  definition as in `scripts/sensitivity.py`) transfers above chance. Primary
  endpoint is external ROC-AUC with a 95% participant-level bootstrap CI (2,000
  resamples, seed 20240517).
  - **Confirmed:** the CI lower bound is > 0.50.
  - **Not confirmed:** otherwise. This is reported as a valid, informative result.
  - The AUC of 0.867 is **not** expected to replicate; magnitude is reported, not
    tested.
- **Secondary (descriptive, no claims of confirmation):**
  1. all-feature logreg / svm_linear / random_forest, plus majority and
     demographics-only baselines (same table as `docs/external_transfer.md`);
  2. the other four feature families;
  3. balanced accuracy, sensitivity, specificity, Brier score;
  4. dataset-identity separability, ds007526 vs. the new cohort.
- **QC / exclusion:** unchanged rules (recording ≥ 60 s; ≥ 20 clean 2-s epochs after
  150 µV peak-to-peak and 1 µV flat rejection). Exclusions are reported by group.

### Cohort-specific adapters (needed to read the data; not analytic choices)
- **ds004584:** recordings are EEGLAB `.set` files (recorded with a BrainVision
  system) with task label `Rest`. *(Corrected 2026-11-08 after download; this
  entry first said `.vhdr`.)*
  The group column is `GROUP` (`PD` / `Control` → HC); demographics are `AGE` and
  `GENDER`. **Pz is the online reference and is not stored.** It is restored as a
  zero channel (`mne.add_reference_channels`) before channel selection, so the
  average reference over the 31 shared channels is computed exactly as for the
  other cohorts.
- **ds003490:** the `Rest` recording contains 1 min eyes closed, 1 min eyes open
  and then an auditory oddball task. Only the **eyes-open** span is analysed (eyes
  open matches the other cohorts; ADR 0002). It runs from the first to the last
  `Eyes Open: Every 1000 ms` event, plus 1 s.
  - The ≥ 60 s duration rule applies to the whole recording.
  - The ≥ 20 clean-epoch rule applies to the eyes-open span.
  - PD participants' ON and OFF sessions are pooled into one participant-level row,
    as for ds002778, so medication state is not separated.
  - Controls have one session.
  - Group is `Group` (`PD` / `CTL` → HC); demographics are `age` and `sex`.

### Alternatives considered and rejected
- **Retraining on ds007526 + ds002778:** more training data, but it changes the
  model whose transfer is being confirmed.
- **Pooling the two new cohorts:** pooling hides the site-to-site variation this
  project studies.
- **Testing only the full feature set:** that tests a different question from the
  one the exploratory result raised.

## Deviations (recorded before any confirmatory result was computed)

### 2026-11-08: PO3/PO4 are missing in most ds004584 recordings
- **Found after download, before preprocessing:** 139 of 149 recordings use a cap
  variant where the PO3/PO4 positions hold I1/I2 and FT9 holds Iz. The other 10
  recordings have the standard layout. Pz (the reference) is missing in all 149.
  The cap variant is not tied to group: the 10 standard-layout recordings are
  8 PD and 2 control.
- **Primary handling:** after restoring Pz and average-referencing all recorded
  channels, rebuild PO3 and PO4 by spherical-spline interpolation
  (`mne.io.Raw.interpolate_bads`) wherever they are absent. The dense 64-channel
  cap has POz, PO7, PO8, P1, P2, O1 and O2 around both sites. The pipeline then
  continues unchanged, so the frozen model and the 31-channel feature definition
  are untouched.
- **Sensitivity:** H1 is re-run with PO3 and PO4 dropped from **every** cohort's
  features before region aggregation (model retrained on ds007526 without them).
  It is reported next to the primary result. It does not replace the primary
  decision.
- **Why this does not bias the test:** this decision was made from channel lists
  alone, before any ds004584 EEG was preprocessed or any model was applied to it.

## Results

### ds004584 (run 2026-11-08; `docs/confirmatory_transfer.md`)
- **QC:** 16 of 149 recordings excluded (5 control, 11 PD), all for having fewer
  than 20 clean epochs. Analysed: n=133 (89 PD, 44 control).
- **H1: confirmed.** Relative-power logreg external AUC **0.733 [0.643, 0.813]**,
  balanced accuracy 0.660 [0.576, 0.747].
- **Sensitivity** (PO3/PO4 dropped from all cohorts): AUC 0.740 [0.651, 0.820].
  The result does not depend on the interpolation.
- **Secondary (descriptive):**
  - Every feature family transfers to about the same degree (AUC 0.723–0.749).
  - All-feature logreg: AUC 0.857 [0.788, 0.916], balanced accuracy 0.722.
  - Linear SVM: AUC 0.811. Random forest: AUC 0.772.
  - Demographics-only model: AUC 0.462, at chance. In this cohort the PD group is
    slightly younger than controls (68.4 vs 71.2 years) and more often male (70% vs
    52%).
  - Dataset identity (ds007526 vs ds004584): logreg AUC 0.916.

### Interpretation (ds004584)
- The pre-registered claim holds on an independent site three times larger than
  ds002778.
- The secondary results **do not support** the specific claim that *normalized*
  features are what transfer (ADR 0010). Absolute, log, slowing and complexity
  features transfer just as well to ds004584. Their failure on ds002778 is better
  read as small-sample variability (n=30) than as a general property.
- Revised picture: features learned on ds007526 carry real, demographics-independent
  disease signal to at least two other sites. That signal sits alongside large
  site/acquisition differences (dataset identity AUC 0.92–0.95).
- These are group-level estimates from a research pipeline, not a diagnostic test.
- ds003490 (step 1b) is still to come and is reported separately.

## Consequences
- Any later change to this plan must be recorded here as a dated **deviation**,
  with its reason, before results are interpreted.
- The two cohorts give three external tests of one frozen model. A model that
  transfers to all three is meaningful evidence. Failure on the new cohorts would
  mean the ds002778 result was likely a small-sample or forking-paths artefact.
- Research tool only: no result here is a diagnostic claim.
