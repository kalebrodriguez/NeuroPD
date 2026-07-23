# ADR 0002: Verify resting eye condition before external analysis

- **Date:** 2026-07-23
- **Status:** accepted

## Context
ds007526 resting-state recordings are documented as **eyes-open**. ds002778's eye
condition is not established from the metadata inspected so far. Eyes-open vs
eyes-closed strongly modulates posterior alpha power, a core candidate biomarker,
so an undetected mismatch would confound cross-dataset comparisons.

## Decision
Make **verifying the ds002778 eye condition the first task of Milestone 1**, read
from the real BIDS sidecars/`README`/task metadata. Do not assume the conditions
match. If they differ, document the mismatch and propose scientifically defensible
handling (e.g. condition-matched subset if available, explicit modelling of the
condition as a covariate, restricting alpha-sensitive comparisons, or a
sensitivity analysis) **before** running the external evaluation.

## Alternatives
- Assume both are eyes-open/closed and proceed (rejected: violates the "never
  assume" rule and risks a serious confound).

## Scientific justification
Alpha power and peak alpha frequency differ systematically with eye state;
comparing an eyes-open cohort to an eyes-closed cohort could produce apparent
"disease" effects that are really condition effects.

## Consequences
If conditions differ and cannot be matched, some spectral comparisons will carry a
documented caveat, and the generalization result must be interpreted with the eye
condition as a candidate explanation for any performance drop.
