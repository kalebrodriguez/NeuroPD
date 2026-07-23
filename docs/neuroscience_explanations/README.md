# Neuroscience & Statistics Teaching Notes

Plain-language explanations of the concepts behind NeuroPD (spec Section 19.3).
Each note explains the concept, why it matters here, and how the code implements
it. Notes are added alongside the milestones that use them.

Planned notes:

- What EEG measures; frequency bands; spectral power
- Spectral slowing; peak alpha frequency
- Entropy and signal complexity
- Functional connectivity; volume conduction
- Artifact rejection
- **Participant-level leakage** (see `docs/decisions/` and `tests/test_splits.py`)
- Internal vs external validation; confounding; calibration

Until the dedicated notes land, the README, `docs/limitations.md`, and the decision
records under `docs/decisions/` capture the core rationale.
