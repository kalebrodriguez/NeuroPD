# ADR 0017: Do EEG slowing markers track clinical severity within PD at two sites? (pre-registered)

- **Date:** 2026-11-08
- **Status:** accepted (written and committed before any EEG-clinical association was computed)

## Context
Every analysis so far asks whether EEG separates PD from controls. Two cohorts also
record clinical severity for their PD participants:

| cohort | cognition | motor | PD n after QC |
| --- | --- | --- | --- |
| ds007526 (Tel Aviv) | MoCA | MDS-UPDRS part III (documented) | 106 |
| ds004584 (Iowa) | MoCA | `UPDRS`, documented only as "UPDRS score" | 89 |

That allows a replication question that does not depend on PD/control
classification: **does the same EEG marker relate to severity in the same direction
at both sites?**

EEG slowing (lower posterior peak alpha frequency, higher theta relative to alpha)
is the most consistently reported resting-EEG correlate of cognitive impairment in
PD. That makes it the natural pre-specified test. The owner asked to continue to the
next stage (2026-11-08). No new data are needed.

The only things inspected before writing this ADR were the clinical columns'
availability and distributions. No EEG-clinical association was computed.

## Decision: frozen analysis plan
- **Participants:** PD participants who passed QC in ds007526 and ds004584, with a
  non-missing score. Controls are excluded because the question is about severity
  within the disease.
- **Features:** the existing frozen 230-feature participant matrices; nothing is
  re-extracted.
- **Primary (H3, cognition), with exactly two pre-specified markers:**
  1. `paf__occipital__median` (occipital peak alpha frequency). Predicted: a
     **positive** association with MoCA.
  2. **Global theta/alpha ratio:** the mean of the five
     `theta_alpha_ratio__<region>__median` columns. Predicted: a **negative**
     association with MoCA.
- **Statistic:** Spearman partial correlation controlling for age. Ranks of
  feature, score and age are taken; age is regressed out of the feature and score
  ranks, and the residuals are correlated. A two-sided p-value comes from the t
  distribution with n - 3 degrees of freedom, plus a 95% bootstrap CI (2,000
  participant resamples, seed 20240517).
- **Replication criterion, per marker:**
  - Bonferroni α = 0.025 (two markers).
  - The marker **replicates** if, in **both** cohorts, the partial correlation has
    the predicted sign and p < 0.025.
  - H3 is supported if at least one marker replicates.
- **Secondary (motor, descriptive):** the same two markers against motor severity
  (ds007526 `updrs_part_iii`; ds004584 `UPDRS`), with no direction predicted.
  Because the ds004584 scale is undocumented, motor results are descriptive only.
- **Exploratory (clearly labelled):** every `__median` feature against MoCA in each
  cohort, with Benjamini-Hochberg FDR within each cohort. Reported:
  - how many features pass FDR in each cohort;
  - cross-cohort agreement of the 115 correlation signs (fraction agreeing, and the
    Spearman correlation of the two coefficient vectors).

## Alternatives
- **Predicting scores with a regression model trained on one site:** this adds
  model choices and is harder to interpret than a pre-specified association test.
  Deferred.
- **Including controls:** that would mix the disease effect with severity.
- **ds002778 (MMSE, n=15 PD) and ds003490:** too small or no matched scale.
  Excluded in advance.

## Consequences
- A replicated marker would be the project's first interpretable, cross-site
  biological association within PD.
- A null result would say the severity signal is not robust across sites with
  these features. That is still informative.
- These are association analyses on observational research data. They are not
  diagnostic or prognostic claims (spec Section 6.5).
