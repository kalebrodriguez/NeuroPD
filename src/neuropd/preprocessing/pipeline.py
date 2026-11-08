"""Configurable resting-state preprocessing pipeline (spec Section 10).

Order of operations (conservative profile; see ADR 0005):
1. normalize channel names (and, if configured, restore an unstored online
   reference channel as zeros and interpolate absent shared channels; ADR 0013)
2. restrict to the shared scalp channels (harmonization; Section 11)
3. set a standard montage
4. notch filter at the per-dataset line frequency (ADR 0004), if within band
5. band-pass filter
6. resample to the shared rate
7. average reference
8. fixed-length epoching
9. peak-to-peak / flat epoch rejection
10. QC metrics + predeclared exclusion decision

Raw inputs are never modified in place (a copy is loaded). The line frequency is
supplied by the caller (per dataset), not hard-coded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neuropd.config import PreprocessingConfig
from neuropd.data.loaders import Recording
from neuropd.logging import get_logger
from neuropd.preprocessing import channels as ch
from neuropd.preprocessing.artifacts import peak_to_peak_flat, peak_to_peak_reject
from neuropd.preprocessing.quality import QCResult, decide_exclusion

_LOG = get_logger("neuropd.preprocessing")


def _interpolate_absent(raw: Any, channels: list[str], montage: str) -> list[str]:
    """Add absent ``channels`` as bad zero channels and spline-interpolate them.

    Returns the list of channels that were interpolated (empty if none absent).
    """
    import mne
    import numpy as np

    absent = [c for c in channels if c not in raw.ch_names]
    if not absent:
        return []
    filler = mne.io.RawArray(
        np.zeros((len(absent), raw.n_times)),
        mne.create_info(absent, raw.info["sfreq"], ch_types="eeg"),
        verbose="ERROR",
    )
    raw.add_channels([filler], force_update_info=True)
    ch.set_standard_montage(raw, montage)
    raw.info["bads"] = list(absent)
    raw.set_eeg_reference("average", projection=False, verbose="ERROR")
    raw.interpolate_bads(reset_bads=True, method={"eeg": "spline"}, verbose="ERROR")
    _LOG.debug("Interpolated absent channels: %s", absent)
    return absent


@dataclass
class PreprocResult:
    """Output of preprocessing a single recording."""

    epochs: Any  # mne.Epochs (None if excluded before epoching)
    qc: QCResult


def preprocess_raw(
    raw: Any,
    cfg: PreprocessingConfig,
    *,
    line_freq: float,
    shared_channels: list[str],
    recording: Recording,
    restore_reference: str | None = None,
    interpolate_missing: list[str] | None = None,
) -> PreprocResult:
    """Preprocess one loaded ``raw`` recording into clean epochs + QC.

    Parameters
    ----------
    raw:
        A loaded ``mne.io.Raw`` (will be copied; the input is not modified).
    cfg:
        Validated preprocessing configuration.
    line_freq:
        Electrical line frequency for this dataset in Hz (ds002778=60, ds007526=50).
    shared_channels:
        The channels to keep (audit-derived shared set).
    recording:
        Metadata for QC bookkeeping.
    restore_reference:
        Name of the online reference electrode when the dataset does not store it
        (ds004584: ``Pz``). It is added back as a zero channel before channel
        selection, so the later average reference recovers its activity. ``None``
        (the default) leaves the recording unchanged.
    interpolate_missing:
        Shared channels to rebuild by spherical-spline interpolation **if absent**
        from the recording (ds004584 cap variant lacks PO3/PO4; ADR 0013). All
        recorded channels are average-referenced first and used as interpolation
        support. Channels already present are never touched.
    """
    import mne

    raw = raw.copy().load_data(verbose="ERROR")
    sfreq_in = float(raw.info["sfreq"])
    duration_s = raw.n_times / sfreq_in

    ch.normalize_channel_names(raw)
    if restore_reference is not None and restore_reference not in raw.ch_names:
        mne.add_reference_channels(raw, ref_channels=[restore_reference], copy=False)
    if interpolate_missing:
        _interpolate_absent(raw, interpolate_missing, cfg.montage)
    ch.pick_shared_channels(raw, shared_channels)
    ch.set_standard_montage(raw, cfg.montage)

    nyquist_in = sfreq_in / 2.0
    if cfg.apply_notch and 0 < line_freq < nyquist_in:
        raw.notch_filter(freqs=line_freq, verbose="ERROR")

    raw.filter(
        l_freq=cfg.bandpass_low_hz,
        h_freq=cfg.bandpass_high_hz,
        verbose="ERROR",
    )

    if abs(sfreq_in - cfg.resample_hz) > 1e-6:
        raw.resample(cfg.resample_hz, verbose="ERROR")

    raw.set_eeg_reference(cfg.reference, projection=False, verbose="ERROR")

    overlap_s = cfg.epoch_length_s * cfg.epoch_overlap
    epochs = mne.make_fixed_length_epochs(
        raw, duration=cfg.epoch_length_s, overlap=overlap_s, preload=True, verbose="ERROR"
    )
    n_total = len(epochs)
    epochs.drop_bad(
        reject=peak_to_peak_reject(cfg.reject_peak_to_peak_uv),
        flat=peak_to_peak_flat(cfg.flat_peak_to_peak_uv),
        verbose="ERROR",
    )
    n_clean = len(epochs)

    excluded, reasons = decide_exclusion(
        duration_s=duration_s,
        n_epochs_clean=n_clean,
        min_recording_duration_s=cfg.min_recording_duration_s,
        min_clean_epochs=cfg.min_clean_epochs,
    )
    qc = QCResult(
        dataset=recording.dataset,
        participant_id=recording.participant_id,
        group=recording.group,
        session=recording.session,
        duration_s=duration_s,
        sfreq_in_hz=sfreq_in,
        n_channels=len(shared_channels),
        n_epochs_total=n_total,
        n_epochs_clean=n_clean,
        excluded=excluded,
        reasons=reasons,
    )
    _LOG.info(
        "%s/%s%s: %d/%d clean epochs (%.0f%% kept)%s",
        recording.dataset,
        recording.participant_id,
        f" {recording.session}" if recording.session else "",
        n_clean,
        n_total,
        100.0 * (n_clean / n_total if n_total else 0.0),
        f" EXCLUDED [{'; '.join(reasons)}]" if excluded else "",
    )
    return PreprocResult(epochs=epochs, qc=qc)
