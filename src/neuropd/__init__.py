"""NeuroPD: cross-dataset validation of explainable EEG biomarkers for Parkinson's disease.

This package provides a reproducible, participant-level research pipeline for
resting-state EEG analysis. It is a *research tool*, not a medical device, and
must never be described as diagnosing Parkinson's disease.

The public API is intentionally small during early milestones; scientific modules
under :mod:`neuropd.preprocessing`, :mod:`neuropd.features`, :mod:`neuropd.modeling`,
and :mod:`neuropd.evaluation` are scaffolded and will be implemented in later
milestones as described in ``AGENTS.md`` and ``docs/``.
"""

from __future__ import annotations

__all__ = ["__version__"]

# Kept in sync with pyproject; a single source of truth is introduced when the
# package is first released. During scaffolding this mirrors the project version.
__version__ = "0.0.0"
