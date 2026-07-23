"""Artifact-rejection helpers (spec Section 10.2).

The conservative pipeline uses a simple, fully reproducible amplitude criterion
(peak-to-peak thresholds) applied to fixed-length epochs, plus flat-epoch
rejection. ICA is intentionally not used in the conservative profile to avoid
subjective, hard-to-reproduce component choices; it may be added later as a
labelled sensitivity analysis.
"""

from __future__ import annotations

_UV_TO_V = 1e-6


def peak_to_peak_reject(threshold_uv: float | None) -> dict[str, float] | None:
    """Build an MNE ``reject`` dict (volts) from a microvolt peak-to-peak threshold."""
    if threshold_uv is None:
        return None
    return {"eeg": threshold_uv * _UV_TO_V}


def peak_to_peak_flat(threshold_uv: float | None) -> dict[str, float] | None:
    """Build an MNE ``flat`` dict (volts) from a microvolt peak-to-peak threshold."""
    if threshold_uv is None:
        return None
    return {"eeg": threshold_uv * _UV_TO_V}
