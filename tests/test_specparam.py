"""Validation of the peak-separated aperiodic fit (ADR 0015), offline."""

from __future__ import annotations

import numpy as np
import pytest

from neuropd.config import PsdConfig
from neuropd.features.specparam_features import (
    SpecparamSettings,
    fit_specparam,
    mean_psd,
    participant_aperiodic_row,
)
from neuropd.features.spectral import aperiodic_fit

pytest.importorskip("fooof")


def _spectrum(exponent: float, alpha_height: float, offset: float = -10.0):
    f = np.arange(0.5, 45.5, 0.5)
    log_ap = offset - exponent * np.log10(f)
    log_peak = alpha_height * np.exp(-((f - 10.0) ** 2) / (2 * 1.2**2))
    return f, 10 ** (log_ap + log_peak)


@pytest.mark.parametrize("exponent", [0.8, 1.2, 1.8])
def test_specparam_recovers_exponent_despite_alpha_peak(exponent: float) -> None:
    f, p = _spectrum(exponent, alpha_height=0.8)
    est, offset, r2 = fit_specparam(f, p, SpecparamSettings())
    ll, _ = aperiodic_fit(f, p, 2.0, 40.0)
    assert abs(est - exponent) < 0.05
    assert abs(est - exponent) < abs(ll - exponent)  # log-log is pulled by the peak
    assert offset == pytest.approx(-10.0, abs=0.1)
    assert r2 > 0.99


def test_fit_specparam_returns_nan_on_degenerate_spectrum() -> None:
    f = np.arange(0.5, 45.5, 0.5)
    assert all(np.isnan(fit_specparam(f, np.zeros_like(f), SpecparamSettings())))


def test_settings_load_from_committed_config() -> None:
    s = SpecparamSettings.from_yaml()
    assert s == SpecparamSettings()


def test_participant_row_has_region_features() -> None:
    rng = np.random.default_rng(0)
    sfreq, n_times = 250.0, 500
    t = np.arange(n_times) / sfreq
    chans = ["Fz", "C3", "Pz", "O1", "T7"]
    sig = np.cumsum(rng.normal(0, 1e-6, (8, len(chans), n_times)), axis=-1)
    sig += 5e-6 * np.sin(2 * np.pi * 10 * t)
    sig -= sig.mean(axis=-1, keepdims=True)
    psd_cfg = PsdConfig(window_s=2.0, overlap=0.5, fmax=45.0)
    freqs, psd = mean_psd(sig, sfreq, psd_cfg)
    assert psd.shape == (len(chans), len(freqs))
    row = participant_aperiodic_row(sig, sfreq, chans, psd_cfg, SpecparamSettings())
    assert any(k.startswith("sp_exponent__") for k in row)
    assert all(np.isfinite(v) for k, v in row.items() if k.startswith("sp_exponent"))
