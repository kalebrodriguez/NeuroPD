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

## Results (executed 2026-11-08; `docs/clinical.md`)
PD participants after QC with a MoCA score: ds007526 n=103 (three of 106 lack a
MoCA score) and ds004584 n=89. Age-partialled Spearman r [95% bootstrap CI]:

| marker (predicted) | ds007526 | ds004584 | replicated |
| --- | --- | --- | --- |
| occipital PAF (+) | +0.006 [-0.19, +0.21], p=0.95 | +0.003 [-0.21, +0.23], p=0.98 | no |
| global theta/alpha ratio (-) | **-0.260** [-0.44, -0.08], p=0.008 | **-0.287** [-0.48, -0.06], p=0.007 | **yes** |

- **H3 supported.** The global theta/alpha ratio replicates: predicted sign, and
  p < 0.025 at both sites, with similar magnitudes.
- Occipital peak alpha frequency shows no association with MoCA at either site.
- **Motor (descriptive):** a higher theta/alpha ratio goes with worse motor scores
  at both sites (+0.232, p=0.019; +0.197, p=0.065). PAF does not (−0.19, −0.07).
- **Exploratory:**
  - 16 of 115 median features pass FDR in ds007526 and none in ds004584.
  - The two sites agree in sign on 59% of the features, and the coefficient vectors
    correlate at +0.36.
  - The strongest MoCA feature at both sites is frontal relative alpha power
    (+0.36 and +0.26).

## Interpretation
- A pre-specified EEG slowing index (more theta relative to alpha, averaged over the
  scalp) relates to poorer cognition within PD, with the same direction and similar
  size (r ≈ −0.27) at two independent sites on different continents and different
  hardware. It is the project's first replicated **within-disease** association.
  It holds up where the PD-vs-control models varied by site.
- The effect is modest: about 7% of rank variance after age.
- Peak alpha frequency, often reported as a slowing marker, did **not** relate to
  MoCA at either site. The association here is carried by the theta/alpha balance,
  not by a shift of the alpha peak.
- The exploratory scan shows the broader feature-severity pattern only partly
  agrees across sites, so the replicated finding is specific to the pre-specified
  marker, not to a general cross-site pattern.
- Observational association in research data. It is not a diagnostic or
  prognostic tool.
