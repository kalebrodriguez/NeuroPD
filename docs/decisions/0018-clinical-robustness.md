# ADR 0018: Robustness of the replicated theta/alpha-cognition association (pre-declared)

- **Date:** 2026-11-10
- **Status:** accepted (written and committed before any robustness result was computed)

## Context
ADR 0017 found that, within PD, a global theta/alpha ratio is associated with lower
MoCA after controlling for age, at both sites with severity data (ds007526
r = −0.260, ds004584 r = −0.287, both p < 0.025). It is the project's only
replicated positive result, so it should be stress-tested before anyone relies on
it. The owner asked to continue (2026-11-10). No new data are needed.

## Decision: pre-declared checks
These use the same participants, features and statistic as ADR 0017: PD after QC
with MoCA; Spearman partial correlation; two-sided t-test p; bootstrap CI.

1. **Age + sex.** Add sex as a covariate.
2. **Age + sex + motor severity.** Add the motor score (ds007526 MDS-UPDRS III;
   ds004584 `UPDRS`, scale undocumented). This asks whether the cognition link is
   independent of motor severity.
3. **Outlier robustness.** Drop participants whose theta/alpha ratio is more than
   3 robust SDs (MAD × 1.4826) from their cohort's median, then repeat the
   age-only test.
4. **Decomposition (descriptive).** Global relative theta power and global relative
   alpha power, each against MoCA (age-partialled). This shows which side of the
   ratio carries the association.
5. **Topography (descriptive).** The theta/alpha ratio per region (5 regions)
   against MoCA (age-partialled). Reported as sign consistency across regions and
   cohorts.
6. **Pooled estimate (descriptive).** Fixed-effect Fisher-z combination of the two
   cohorts' age-partialled r, with a 95% CI. The weight is n − 3 per cohort.

**Robustness criterion, decided in advance:** the association is called **robust**
if, under checks 1, 2 and 3, it keeps the negative sign with p < 0.05 at **both**
sites. Failing any of these is reported as a limitation of ADR 0017, not hidden.
Checks 4-6 are descriptive.

## Consequences
- A robust result strengthens the within-PD association as the project's most
  generalizable finding. It remains observational and non-diagnostic.
- If the association does not survive the motor covariate, the more parsimonious
  reading is a general severity marker rather than a cognitive one.
