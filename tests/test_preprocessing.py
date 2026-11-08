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


def test_restore_reference_recovers_average_referenced_data() -> None:
    """A Pz-referenced recording without Pz must match the original after restore.

    ds004584 stores data referenced to Pz without the Pz channel (ADR 0013). Adding
    Pz back as zeros and then average-referencing must give the same epochs as
    average-referencing the original (reference-free) recording.
    """
    raw = _synthetic_raw(sfreq=500.0, seconds=60.0)
    cfg = PreprocessingConfig()
    expected = preprocess_raw(
        raw, cfg, line_freq=60.0, shared_channels=SHARED, recording=_recording()
    ).epochs.get_data()

    pz_referenced = raw.copy()
    data = pz_referenced.get_data()
    data -= data[pz_referenced.ch_names.index("Pz")]
    pz_referenced._data = data
    pz_referenced.drop_channels(["Pz"])
    restored = preprocess_raw(
        pz_referenced,
        cfg,
        line_freq=60.0,
        shared_channels=SHARED,
        recording=_recording(),
        restore_reference="Pz",
    ).epochs
    assert restored.ch_names == SHARED
    np.testing.assert_allclose(restored.get_data(), expected, atol=1e-9)


def test_missing_reference_without_restore_fails_loudly() -> None:
    raw = _synthetic_raw(sfreq=500.0, seconds=60.0)
    raw.drop_channels(["Pz"])
    with pytest.raises(ValueError, match="missing expected shared channels"):
        preprocess_raw(
            raw,
            PreprocessingConfig(),
            line_freq=60.0,
            shared_channels=SHARED,
            recording=_recording(),
        )


def _smooth_field_raw(names: list[str], sfreq: float = 500.0, seconds: float = 60.0):
    """Synthetic EEG whose amplitude varies smoothly over the scalp (interpolable)."""
    montage = mne.channels.make_standard_montage("standard_1005")
    pos = montage.get_positions()["ch_pos"]
    n = int(sfreq * seconds)
    t = np.arange(n) / sfreq
    rng = np.random.default_rng(1)
    s1 = np.sin(2 * np.pi * 10.0 * t)
    s2 = np.sin(2 * np.pi * 6.0 * t + 0.7)
    data = np.zeros((len(names), n))
    for i, name in enumerate(names):
        x, y, _z = pos[name]
        data[i] = 20e-6 * ((1 + 8 * x) * s1 + (1 + 8 * y) * s2) + rng.normal(0, 0.2e-6, n)
    raw = mne.io.RawArray(data, mne.create_info(names, sfreq, "eeg"), verbose="ERROR")
    raw.set_montage(montage)
    return raw


DENSE = [
    "Fp1",
    "Fp2",
    "AF3",
    "AF4",
    "F7",
    "F3",
    "Fz",
    "F4",
    "F8",
    "FC5",
    "FC1",
    "FC2",
    "FC6",
    "T7",
    "C3",
    "Cz",
    "C4",
    "T8",
    "CP5",
    "CP1",
    "CP2",
    "CP6",
    "P7",
    "P3",
    "Pz",
    "P4",
    "P8",
    "P1",
    "P2",
    "PO7",
    "PO3",
    "POz",
    "PO4",
    "PO8",
    "O1",
    "Oz",
    "O2",
]
PARIETAL_SHARED = ["P3", "Pz", "P4", "PO3", "PO4", "O1", "Oz", "O2"]


def test_interpolate_missing_rebuilds_absent_channels() -> None:
    raw = _smooth_field_raw(DENSE)
    cfg = PreprocessingConfig()
    ref = preprocess_raw(
        raw, cfg, line_freq=60.0, shared_channels=PARIETAL_SHARED, recording=_recording()
    ).epochs.get_data()

    holed = raw.copy().drop_channels(["PO3", "PO4"])
    # A non-scalp channel stored as EEG (ds004584 "Resp") must not break the spline.
    resp = mne.io.RawArray(
        np.random.default_rng(2).normal(0, 50e-6, (1, holed.n_times)),
        mne.create_info(["Resp"], holed.info["sfreq"], "eeg"),
        verbose="ERROR",
    )
    holed.add_channels([resp], force_update_info=True)
    got = preprocess_raw(
        holed,
        cfg,
        line_freq=60.0,
        shared_channels=PARIETAL_SHARED,
        recording=_recording(),
        interpolate_missing=["PO3", "PO4"],
    ).epochs
    assert got.ch_names == PARIETAL_SHARED
    out = got.get_data()
    for ch_name in ("PO3", "PO4"):
        i = PARIETAL_SHARED.index(ch_name)
        r = np.corrcoef(out[:, i].ravel(), ref[:, i].ravel())[0, 1]
        assert r > 0.95, (ch_name, r)


def test_interpolate_missing_leaves_present_channels_untouched() -> None:
    raw = _smooth_field_raw(DENSE)
    cfg = PreprocessingConfig()
    kwargs = {"line_freq": 60.0, "shared_channels": PARIETAL_SHARED, "recording": _recording()}
    plain = preprocess_raw(raw, cfg, **kwargs).epochs.get_data()
    noop = preprocess_raw(raw, cfg, interpolate_missing=["PO3", "PO4"], **kwargs)
    np.testing.assert_allclose(noop.epochs.get_data(), plain)
