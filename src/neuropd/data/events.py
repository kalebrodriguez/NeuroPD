"""BIDS events helpers for selecting a condition span within a recording.

ds003490 stores 1 min eyes closed, 1 min eyes open and an oddball task in one
``task-Rest`` recording, with one ``Eyes Open: Every 1000 ms`` marker per second of
the eyes-open block. ADR 0013 pre-registers the analysed span as the first to the
last such marker, plus 1 s.
"""

from __future__ import annotations

from pathlib import Path

from neuropd.data.audit import read_tsv


def events_path(recording_path: Path) -> Path:
    """Return the BIDS ``*_events.tsv`` sidecar for an ``*_eeg.<ext>`` recording."""
    stem = recording_path.name.rsplit("_eeg", 1)[0]
    return recording_path.with_name(f"{stem}_events.tsv")


def event_window(
    events_tsv: Path,
    trial_type_prefix: str,
    pad_after_s: float = 0.0,
    max_gap_s: float = 2.0,
) -> tuple[float, float]:
    """Return ``(tmin, tmax)`` in seconds of the FIRST contiguous block of events
    whose ``trial_type`` starts with ``trial_type_prefix``, extended by
    ``pad_after_s`` after the block's last event.

    A block ends where consecutive matching onsets are more than ``max_gap_s``
    apart (ds003490 ``sub-019 ses-01`` repeats the eyes-open block after an
    eyes-closed block; ADR 0013 deviation). Raises ``ValueError`` if no matching
    event exists (fail loudly rather than analysing the wrong condition).
    """
    onsets = sorted(
        float(row["onset"])
        for row in read_tsv(events_tsv)
        if str(row.get("trial_type", "")).startswith(trial_type_prefix)
    )
    if not onsets:
        raise ValueError(f"No '{trial_type_prefix}' events in {events_tsv}")
    end = onsets[0]
    for onset in onsets[1:]:
        if onset - end > max_gap_s:
            break
        end = onset
    return onsets[0], end + pad_after_s
