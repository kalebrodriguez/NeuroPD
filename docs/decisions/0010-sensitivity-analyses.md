# ADR 0010: Sensitivity analyses

- **Date:** 2026-07-24
- **Status:** accepted

## Context
The main findings (Milestones 4-6) rest on several defensible-but-arguable choices:
region-level feature aggregation, the demographic confound, and a broad feature set.
Section 14.5 requires a small set of pre-declared robustness checks rather than an
open-ended search. All values below are executed (`scripts/sensitivity.py`,
`docs/sensitivity.md`), development cohort ds007526 (internal, participant-grouped
5x5 CV) and the frozen external transfer to ds002778 (n=30, so external point
estimates have wide intervals — treat as directional).

## Analyses and results

### 1. Channel harmonization (region vs. exact shared channels)
Region-level (210 features): internal AUC 0.718, external AUC **0.671**.
Channel-level (1302 features): internal AUC 0.715, external AUC **0.529** (chance).
→ Region aggregation is decisively more transferable; the high-dimensional
channel-level representation overfits dataset-specific spatial detail and does not
travel. **Validates the ADR 0006 default.**

### 2. Age/sex adjustment (does EEG add signal beyond demographics?)
Demographics-only: AUC 0.688. EEG: 0.718. EEG with age/sex linearly partialled out
in-fold: **AUC 0.668** (still above chance). EEG + demographics: 0.717.
→ Two things are true at once: demographics is a strong confound (its balanced
accuracy 0.645 exceeds raw EEG's 0.563), **and** EEG carries signal *independent* of
age/sex (residualized AUC 0.668 > 0.5). EEG is not merely a demographic proxy — but
demographic confounding is real and must stay in view.

### 3. Feature family (which groups carry / transfer signal)
| family | internal AUC | external AUC |
|---|---|---|
| relative power | 0.687 | **0.867** |
| absolute power | 0.722 | 0.591 |
| log power | 0.773 | 0.640 |
| slowing (paf/sef/ratios) | 0.761 | 0.476 |
| complexity | 0.704 | 0.493 |
→ The strongest result: **relative (scale-normalized) band power transfers far
better than any other family** (external AUC ~0.87 vs 0.48-0.64), while log/absolute
power and slowing win *internally* but transfer poorly. Scale- and montage-sensitive
features carry dataset-specific information that inflates within-cohort performance
and then fails to generalize. This nuances the headline: it is not that *no* EEG
feature transfers — it is that the *normalized* features do, and the pipeline's full
feature set dilutes them.

## Consequences
- Region-level, relative-power features are the transferable core; a future model
  should prefer them (and consider dropping absolute/log power for cross-dataset use).
- The demographic confound stands, but EEG has independent signal — so the project's
  conclusion is "modest, normalization-dependent transfer," not "no transfer."
- All external numbers are n=30 point estimates (no CIs here); they are directional
  evidence, not confirmation. A third cohort and harmonization (e.g. ComBat) remain
  the right next steps (stretch goals).
