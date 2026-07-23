"""Spectral features (spec Section 12.1).

Interpretable, physiologically motivated frequency-domain features computed from a
Welch power spectral density (PSD). All functions operate on a single-channel,
single-epoch 1-D signal (or a precomputed ``(freqs, psd)`` pair) so that each has
a small synthetic-signal unit test (Section 12.5). Band boundaries come from
configuration, never hard-coded here.

Units
-----
Input signals are in volts (MNE default). Absolute band power is therefore in
V**2 (integral of PSD, V**2/Hz, over a frequency band). Relative power is
dimensionless (fraction of total in-band power). Frequencies are in Hz.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sp_signal

from neuropd.config import PsdConfig


def compute_psd(sig: np.ndarray, sfreq: float, cfg: PsdConfig) -> tuple[np.ndarray, np.ndarray]:
    """Welch PSD of a 1-D signal, truncated to ``[0, cfg.fmax]``.

    Returns ``(freqs, psd)`` with ``psd`` in V**2/Hz. ``nperseg`` is
    ``window_s * sfreq`` capped at the signal length so short epochs still work.
    """
    sig = np.asarray(sig, dtype=float)
    if sig.ndim != 1:
        raise ValueError(f"compute_psd expects a 1-D signal, got shape {sig.shape}")
    nperseg = min(len(sig), max(1, round(cfg.window_s * sfreq)))
    noverlap = round(cfg.overlap * nperseg)
    freqs, psd = sp_signal.welch(sig, fs=sfreq, nperseg=nperseg, noverlap=noverlap)
    keep = freqs <= cfg.fmax
    return freqs[keep], psd[keep]


def band_power(freqs: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
    """Absolute power in ``[low, high)`` Hz: the integral of the PSD over the band.

    Uses trapezoidal integration over the PSD bins falling in the band. Returns
    ``nan`` if fewer than two bins fall in the band (so callers can flag it).
    """
    mask = (freqs >= low) & (freqs < high)
    if np.count_nonzero(mask) < 2:
        return float("nan")
    return float(np.trapezoid(psd[mask], freqs[mask]))


def total_power(freqs: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
    """Total PSD integral over ``[low, high]`` Hz (inclusive upper edge)."""
    mask = (freqs >= low) & (freqs <= high)
    if np.count_nonzero(mask) < 2:
        return float("nan")
    return float(np.trapezoid(psd[mask], freqs[mask]))


def peak_alpha_frequency(freqs: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
    """Frequency (Hz) of maximum PSD within the alpha band ``[low, high]``.

    A robust, interpretable marker of spectral slowing: PD is associated with a
    lower peak alpha frequency. Returns ``nan`` if the band is empty.
    """
    mask = (freqs >= low) & (freqs <= high)
    if not np.any(mask):
        return float("nan")
    band_freqs = freqs[mask]
    band_psd = psd[mask]
    return float(band_freqs[np.argmax(band_psd)])


def spectral_edge_frequency(
    freqs: np.ndarray, psd: np.ndarray, quantile: float, fmax: float
) -> float:
    """Frequency (Hz) below which ``quantile`` of the total power (0..fmax) lies.

    Spectral slowing lowers the spectral edge frequency. Returns ``nan`` if there
    is no positive power in range.
    """
    mask = freqs <= fmax
    f = freqs[mask]
    p = psd[mask]
    cumulative = np.cumsum(p)
    if cumulative[-1] <= 0:
        return float("nan")
    threshold = quantile * cumulative[-1]
    idx = min(np.searchsorted(cumulative, threshold), len(f) - 1)
    return float(f[idx])


def spectral_entropy(freqs: np.ndarray, psd: np.ndarray, fmax: float) -> float:
    """Normalized spectral entropy of the PSD over ``[0, fmax]`` (0..1).

    The PSD is normalized to a probability distribution and its Shannon entropy is
    divided by ``log(n_bins)``. A flat (white) spectrum approaches 1; a single
    dominant peak approaches 0. Returns ``nan`` if there is no positive power.
    """
    mask = freqs <= fmax
    p = psd[mask]
    total = p.sum()
    if total <= 0 or p.size < 2:
        return float("nan")
    prob = p / total
    nonzero = prob[prob > 0]
    entropy = -np.sum(nonzero * np.log(nonzero))
    return float(entropy / np.log(p.size))
