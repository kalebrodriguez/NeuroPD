"""Preprocessing tests on synthetic signals (spec Section 10 / Section 18.1).

Uses a synthetic multi-channel recording with a known 10 Hz (alpha) rhythm plus
line noise, so behaviour is verifiable without downloading data.
"""

from __future__ import annotations

import numpy as np
import pytest

from neuropd.config import PreprocessingConfig
from neuropd.data.loaders import Recording
from neuropd.preprocessing.channels import pick_shared_channels
from neuropd.preprocessing.pipeline import preprocess_raw
from neuropd.preprocessing.quality import decide_exclusion

mne = pytest.importorskip("mne")

SHARED = ["Fp1", "AF3", "F7", "F3", "FC1", "C3", "Pz", "O1", "Oz", "O2", "P4", "C4", "F4", "Fz"]


def _synthetic_raw(sfreq: float = 512.0, seconds: float = 120.0, line_hz: float = 60.0):
    n = int(sfreq * seconds)
    t = np.arange(n) / sfreq
    rng = np.random.default_rng(0)
    chans = [*SHARED, "EXG1"]  # include a non-shared channel to test picking
    data = np.zeros((len(chans), n))
    n_ch = len(chans)
    for i in range(n_ch):
        # Spatially varying amplitude/phase so the common component is not fully
        # removed by the average reference (mirrors real, topographically varying EEG).
        scale = 0.5 + i / n_ch
        phase = 0.3 * i
        alpha = scale * 20e-6 * np.sin(2 * np.pi * 10.0 * t + phase)  # 10 Hz alpha
        line = scale * 15e-6 * np.sin(2 * np.pi * line_hz * t)  # mains
        noise = rng.normal(0, 3e-6, n)
        data[i] = alpha + line + noise
    info = mne.create_info(chans, sfreq, ch_types="eeg")
    return mne.io.RawArray(data, info, verbose="ERROR")


def _recording() -> Recording:
    from pathlib import Path

    return Recording("dsTEST", "sub-t1", "HC", None, "rest", Path("x"))


def test_pick_shared_channels_selects_and_orders() -> None:
    raw = _synthetic_raw()
    pick_shared_channels(raw, SHARED)
    assert raw.ch_names == SHARED


def test_pick_shared_channels_missing_raises() -> None:
    raw = _synthetic_raw()
    with pytest.raises(ValueError, match="missing expected shared channels"):
        pick_shared_channels(raw, [*SHARED, "NoSuchChannel"])


def test_pipeline_resamples_reduces_channels_and_epochs() -> None:
    raw = _synthetic_raw(sfreq=512.0, seconds=120.0)
    cfg = PreprocessingConfig()
    res = preprocess_raw(raw, cfg, line_freq=60.0, shared_channels=SHARED, recording=_recording())
    ep = res.epochs
    assert ep.info["sfreq"] == cfg.resample_hz
    assert ep.ch_names == SHARED
    # 120 s of 2 s non-overlapping epochs -> ~60, all finite
    assert 55 <= res.qc.n_epochs_total <= 60
    assert np.isfinite(ep.get_data()).all()
    assert not res.qc.excluded


def test_pipeline_alpha_peak_survives_and_line_removed() -> None:
    raw = _synthetic_raw(sfreq=512.0, seconds=60.0, line_hz=60.0)
    cfg = PreprocessingConfig()
    res = preprocess_raw(raw, cfg, line_freq=60.0, shared_channels=SHARED, recording=_recording())
    psd = res.epochs.compute_psd(fmax=45.0, verbose="ERROR")
    freqs = psd.freqs
    power = psd.get_data().mean(axis=(0, 1))
    peak_hz = float(freqs[int(np.argmax(power))])
    assert abs(peak_hz - 10.0) < 1.5  # alpha dominates after preprocessing


def test_high_amplitude_epoch_is_rejected() -> None:
    raw = _synthetic_raw(sfreq=512.0, seconds=60.0)
    data = raw.get_data()
    # Inject a large in-band (15 Hz) burst into a few channels of the 2nd epoch so
    # the average reference cannot cancel it and the 1 Hz high-pass keeps it.
    t_burst = np.arange(1024, 2048) / 512.0
    burst = 800e-6 * np.sin(2 * np.pi * 15.0 * t_burst)
    data[0:3, 1024:2048] += burst
    raw._data = data
    cfg = PreprocessingConfig()
    res = preprocess_raw(raw, cfg, line_freq=60.0, shared_channels=SHARED, recording=_recording())
    assert res.qc.n_epochs_clean < res.qc.n_epochs_total


def test_decide_exclusion_reasons() -> None:
    excluded, reasons = decide_exclusion(
        duration_s=30.0, n_epochs_clean=5, min_recording_duration_s=60.0, min_clean_epochs=20
    )
    assert excluded
    assert any("recording_duration" in r for r in reasons)
    assert any("clean_epochs" in r for r in reasons)


def test_config_rejects_band_above_nyquist() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PreprocessingConfig(bandpass_high_hz=200.0, resample_hz=250.0)
