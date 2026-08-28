"""Tests for the aperiodic (1/f) spectral feature (ADR 0012)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from neuropd.config import FeatureConfig, load_yaml
from neuropd.features import spectral as sp
from neuropd.features.aggregate import base_feature_names


def _feature_config() -> FeatureConfig:
    raw = load_yaml(Path(__file__).resolve().parents[1] / "configs/features/interpretable.yaml")
    return FeatureConfig.model_validate(raw)


def test_aperiodic_fit_recovers_known_slope_and_offset() -> None:
    freqs = np.linspace(1.0, 45.0, 200)
    exponent_true, offset_true = 1.8, -2.0
    # psd = 10**offset * f**(-exponent)  ->  log10(psd) = offset - exponent*log10(f)
    psd = 10.0**offset_true * freqs ** (-exponent_true)
    exponent, offset = sp.aperiodic_fit(freqs, psd, fmin=2.0, fmax=40.0)
    assert abs(exponent - exponent_true) < 1e-6
    assert abs(offset - offset_true) < 1e-6


def test_aperiodic_fit_insufficient_bins_returns_nan() -> None:
    freqs = np.array([0.0, 1.0])
    psd = np.array([1.0, 0.5])
    exponent, offset = sp.aperiodic_fit(freqs, psd, fmin=2.0, fmax=40.0)
    assert np.isnan(exponent) and np.isnan(offset)


def test_aperiodic_fit_ignores_nonpositive_power() -> None:
    freqs = np.linspace(1.0, 45.0, 100)
    psd = 10.0 ** (-1.0) * freqs ** (-1.0)
    psd[10:15] = 0.0  # zero-power bins must be dropped, not crash the log fit
    exponent, offset = sp.aperiodic_fit(freqs, psd, fmin=2.0, fmax=40.0)
    assert np.isfinite(exponent) and np.isfinite(offset)


def test_aperiodic_feature_names_toggle_with_flag() -> None:
    cfg = _feature_config()
    cfg_off = cfg.model_copy(
        update={"spectral": cfg.spectral.model_copy(update={"aperiodic": False})}
    )
    cfg_on = cfg.model_copy(
        update={"spectral": cfg.spectral.model_copy(update={"aperiodic": True})}
    )
    names_off = base_feature_names(cfg_off)
    names_on = base_feature_names(cfg_on)
    assert "aperiodic_exponent" not in names_off
    assert "aperiodic_exponent" in names_on
    assert "aperiodic_offset" in names_on
    assert len(names_on) == len(names_off) + 2
