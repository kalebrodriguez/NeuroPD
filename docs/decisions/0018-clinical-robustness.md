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

## Results (executed 2026-11-10; `docs/clinical_robustness.md`)

| check | ds007526 | ds004584 |
| --- | --- | --- |
| ADR 0017 reference (age) | −0.260, p=0.008 | −0.287, p=0.007 |
| 1 age + sex | −0.248, p=0.012 | −0.224, p=0.037 |
| 2 age + sex + motor | −0.230, p=0.023 | −0.212, p=**0.0501** |
| 3 outliers removed | −0.187, p=**0.081** (n=89) | −0.183, p=**0.106** (n=80) |

- **Pre-declared criterion: not robust.** Check 3 fails at both sites, and check 2
  misses p < 0.05 at ds004584 by 0.0001. The sign stays negative in every check.
- **Descriptive:**
  - Relative alpha alone relates to MoCA at both sites (+0.339, p=0.0005; +0.255,
    p=0.016). Relative theta alone does not reach significance at either site
    (−0.129, −0.196).
  - The ratio is negative and p < 0.03 in all five regions at both sites.
  - Pooled age-partialled r = −0.273 [−0.400, −0.135].
- **Post-hoc characterization (not pre-declared):**
  - The theta/alpha ratio is strongly right-skewed (skew ≈ 2.7 in both cohorts).
  - All 14 and 9 excluded participants were on the high (more slowing) side.
  - They had lower MoCA than those retained: mean 22.8 vs 25.7 (ds007526) and
    19.6 vs 24.7 (ds004584).

## Interpretation
- The ADR 0017 replication stands as pre-registered. It does **not** meet this
  stricter robustness bar.
- The association is concentrated in a tail of participants with marked slowing
  and lower cognition. It is not a graded relationship across the whole range:
  without that tail, the remaining correlation is weaker (r ≈ −0.18) and not
  significant at either site.
- The decomposition points to reduced relative alpha rather than increased theta.
- Adjusting for motor severity changes the estimates little (−0.23 / −0.21). That
  argues against a pure general-severity explanation, although ds004584 sits on
  the threshold.
- Honest summary: EEG slowing, mainly lower alpha, marks the more cognitively
  impaired PD participants at both sites. It is a modest, tail-driven association,
  not a robust continuous marker.
