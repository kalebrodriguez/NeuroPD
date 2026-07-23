"""Configurable resting-state preprocessing pipeline (spec Section 10).

Order of operations (conservative profile; see ADR 0005):
1. normalize channel names
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
    """
    import mne

    raw = raw.copy().load_data(verbose="ERROR")
    sfreq_in = float(raw.info["sfreq"])
    duration_s = raw.n_times / sfreq_in

    ch.normalize_channel_names(raw)
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
