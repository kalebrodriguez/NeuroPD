"""Peak-separated aperiodic features via spectral parameterization (ADR 0015).

Fits the FOOOF/specparam model (aperiodic component + Gaussian peaks) once per
participant and channel, on the epoch-averaged Welch PSD, then averages channels
within the five scalp regions. The ADR 0012 log-log fit is recomputed on the same
averaged spectra so the two methods are compared like for like.

The only third-party call is isolated in :func:`fit_specparam`, so replacing
``fooof`` 1.1 with ``specparam`` 2.x once it is stable is a one-function change.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from neuropd.config import PsdConfig, load_yaml
from neuropd.features import spectral as sp
from neuropd.features.aggregate import _region_indices

DEFAULT_CONFIG = Path("configs/features/specparam.yaml")


@dataclass(frozen=True)
class SpecparamSettings:
    """Fit settings fixed in ADR 0015."""

    freq_range: tuple[float, float] = (2.0, 40.0)
    aperiodic_mode: str = "fixed"
    peak_width_limits: tuple[float, float] = (1.0, 8.0)
    max_n_peaks: int = 6
    min_peak_height: float = 0.1
    peak_threshold: float = 2.0

    @classmethod
    def from_yaml(cls, path: Path = DEFAULT_CONFIG) -> SpecparamSettings:
        raw = load_yaml(path)
        return cls(
            freq_range=tuple(raw["freq_range"]),
            aperiodic_mode=str(raw["aperiodic_mode"]),
            peak_width_limits=tuple(raw["peak_width_limits"]),
            max_n_peaks=int(raw["max_n_peaks"]),
            min_peak_height=float(raw["min_peak_height"]),
            peak_threshold=float(raw["peak_threshold"]),
        )


def fit_specparam(
    freqs: np.ndarray, psd: np.ndarray, settings: SpecparamSettings
) -> tuple[float, float, float]:
    """Return ``(exponent, offset, r_squared)`` of a spectral-parameterization fit.

    ``offset`` is in log10(power) units, like the ADR 0012 log-log intercept.
    Returns NaNs if the fit fails (e.g. a flat or non-positive spectrum).
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from fooof import FOOOF

    model = FOOOF(
        peak_width_limits=settings.peak_width_limits,
        max_n_peaks=settings.max_n_peaks,
        min_peak_height=settings.min_peak_height,
        peak_threshold=settings.peak_threshold,
        aperiodic_mode=settings.aperiodic_mode,
        verbose=False,
    )
    mask = (freqs > 0) & (psd > 0)
    if np.count_nonzero(mask) < 5:
        return (float("nan"), float("nan"), float("nan"))
    try:
        model.fit(freqs[mask], psd[mask], list(settings.freq_range))
    except Exception:  # library raises various fit errors
        return (float("nan"), float("nan"), float("nan"))
    if not model.has_model:
        return (float("nan"), float("nan"), float("nan"))
    offset, exponent = model.aperiodic_params_[0], model.aperiodic_params_[-1]
    return (float(exponent), float(offset), float(model.r_squared_))


def mean_psd(data: np.ndarray, sfreq: float, psd_cfg: PsdConfig) -> tuple[np.ndarray, np.ndarray]:
    """Epoch-averaged Welch PSD per channel.

    ``data`` is ``(n_epochs, n_channels, n_times)``; returns ``(freqs, psd)`` with
    ``psd`` shaped ``(n_channels, n_freqs)``.
    """
    n_epochs, n_channels, _ = data.shape
    freqs = None
    acc = None
    for e in range(n_epochs):
        for c in range(n_channels):
            f, p = sp.compute_psd(data[e, c], sfreq, psd_cfg)
            if acc is None:
                freqs, acc = f, np.zeros((n_channels, len(f)))
            acc[c] += p
    assert acc is not None and freqs is not None
    return freqs, acc / n_epochs


APERIODIC_FEATURES = ("sp_exponent", "sp_offset", "sp_r2", "ll_exponent", "ll_offset")


def participant_aperiodic_row(
    data: np.ndarray,
    sfreq: float,
    ch_names: list[str],
    psd_cfg: PsdConfig,
    settings: SpecparamSettings,
) -> dict[str, float]:
    """Region-mean aperiodic features for one participant (both methods)."""
    freqs, psd = mean_psd(data, sfreq, psd_cfg)
    lo, hi = settings.freq_range
    per_channel = np.full((len(ch_names), len(APERIODIC_FEATURES)), np.nan)
    for c in range(len(ch_names)):
        exp_sp, off_sp, r2 = fit_specparam(freqs, psd[c], settings)
        exp_ll, off_ll = sp.aperiodic_fit(freqs, psd[c], lo, hi)
        per_channel[c] = [exp_sp, off_sp, r2, exp_ll, off_ll]
    row: dict[str, float] = {}
    for region, idx in _region_indices(ch_names).items():
        means = np.nanmean(per_channel[idx], axis=0)
        for name, value in zip(APERIODIC_FEATURES, means, strict=True):
            row[f"{name}__{region}"] = float(value)
    return row
