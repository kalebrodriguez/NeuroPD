"""Synthetic-signal feature tests (spec Section 12.5 / Section 18.1).

Each interpretable feature is checked against a signal with known properties: a
10 Hz sine must dominate the alpha band, a pure sine has Hjorth complexity near 1,
an ordered ramp has near-zero permutation entropy while noise approaches 1, and
participant aggregation yields exactly one row per participant.
"""

from __future__ import annotations

import numpy as np
import pytest

from neuropd.config import load_feature_config
from neuropd.features import aggregate as agg
from neuropd.features import complexity as cx
from neuropd.features import spectral as sp
from neuropd.features.matrix import ParticipantRecord, build_feature_frame, feature_columns

SFREQ = 250.0


@pytest.fixture
def cfg():
    return load_feature_config()


def _sine(freq: float, seconds: float = 4.0, sfreq: float = SFREQ, amp: float = 1e-5) -> np.ndarray:
    t = np.arange(0, seconds, 1.0 / sfreq)
    return amp * np.sin(2 * np.pi * freq * t)


def test_alpha_sine_dominates_alpha_band(cfg) -> None:
    freqs, psd = sp.compute_psd(_sine(10.0), SFREQ, cfg.psd)
    bands = cfg.active_bands()
    powers = {b: sp.band_power(freqs, psd, lo, hi) for b, (lo, hi) in bands.items()}
    assert max(powers, key=lambda b: powers[b]) == "alpha"


def test_peak_alpha_frequency_recovers_tone(cfg) -> None:
    freqs, psd = sp.compute_psd(_sine(11.0), SFREQ, cfg.psd)
    lo, hi = cfg.active_bands()["alpha"]
    assert sp.peak_alpha_frequency(freqs, psd, lo, hi) == pytest.approx(11.0, abs=0.75)


def test_relative_power_alpha_is_highest_for_alpha_tone(cfg) -> None:
    values = agg._base_vector(_sine(10.0), SFREQ, cfg)
    names = agg.base_feature_names(cfg)
    rel = {n: v for n, v in zip(names, values, strict=True) if n.startswith("rel_power_")}
    assert max(rel, key=lambda n: rel[n]) == "rel_power_alpha"
    assert rel["rel_power_alpha"] > 0.9


def test_band_power_empty_band_returns_nan(cfg) -> None:
    freqs, psd = sp.compute_psd(_sine(10.0), SFREQ, cfg.psd)
    assert np.isnan(sp.band_power(freqs, psd, 100.0, 120.0))


def test_hjorth_complexity_of_sine_near_one() -> None:
    activity, _mobility, complexity = cx.hjorth_parameters(_sine(10.0))
    assert activity > 0
    assert complexity == pytest.approx(1.0, abs=0.05)


def test_permutation_entropy_ordered_below_noise(rng) -> None:
    ramp = np.linspace(0, 1, 1000)
    noise = rng.standard_normal(1000)
    pe_ramp = cx.permutation_entropy(ramp, order=3, delay=1)
    pe_noise = cx.permutation_entropy(noise, order=3, delay=1)
    assert pe_ramp == pytest.approx(0.0, abs=1e-9)
    assert pe_noise > 0.95
    assert pe_ramp < pe_noise


def test_spectral_entropy_flat_above_peaked(cfg, rng) -> None:
    freqs_n, psd_n = sp.compute_psd(rng.standard_normal(2000) * 1e-6, SFREQ, cfg.psd)
    freqs_s, psd_s = sp.compute_psd(_sine(10.0), SFREQ, cfg.psd)
    se_noise = sp.spectral_entropy(freqs_n, psd_n, cfg.psd.fmax)
    se_sine = sp.spectral_entropy(freqs_s, psd_s, cfg.psd.fmax)
    assert se_noise > se_sine


def test_participant_row_keys_match_feature_names(cfg, rng) -> None:
    ch_names = ["Fp1", "F3", "C3", "Cz", "P3", "O1", "T7"]
    data = rng.standard_normal((12, len(ch_names), int(2 * SFREQ))) * 1e-6
    row = agg.participant_feature_row(data, SFREQ, ch_names, cfg)
    assert set(row) == set(agg.feature_names(cfg, ch_names))
    # region strategy: one value per (base feature x region x stat)
    n_regions = len(agg._region_indices(ch_names))
    expected = len(agg.base_feature_names(cfg)) * n_regions * len(cfg.aggregation.statistics)
    assert len(row) == expected


def test_aggregation_one_row_per_participant(cfg, rng) -> None:
    ch_names = ["Fp1", "F3", "C3", "P3", "O1"]
    records = []
    for i in range(4):
        data = rng.standard_normal((10, len(ch_names), int(2 * SFREQ))) * 1e-6
        feats = agg.participant_feature_row(data, SFREQ, ch_names, cfg)
        records.append(
            ParticipantRecord(
                participant_id=f"sub-{i:02d}",
                dataset="dsX",
                group="PD" if i % 2 else "HC",
                n_sessions=1,
                n_epochs=10,
                features=feats,
            )
        )
    frame = build_feature_frame(records)
    assert len(frame) == 4
    assert frame["participant_id"].is_unique
    assert set(feature_columns(frame)) == set(agg.feature_names(cfg, ch_names))
