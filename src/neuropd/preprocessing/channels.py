"""Channel naming, selection, and montage for cross-dataset harmonization.

Implements the "exact shared-channel subset" strategy (spec Section 11): restrict
each recording to the channels common to both datasets (computed in the audit),
then set a standard montage so downstream referencing and topographies are
comparable. Region-level aggregation (an alternative strategy) reuses
``neuropd.data.regions``.
"""

from __future__ import annotations

from typing import Any


def normalize_channel_names(raw: Any) -> Any:
    """Strip surrounding whitespace from channel names in place; returns ``raw``."""
    mapping = {ch: ch.strip() for ch in raw.ch_names if ch != ch.strip()}
    if mapping:
        raw.rename_channels(mapping)
    return raw


def pick_shared_channels(raw: Any, shared: list[str]) -> Any:
    """Restrict ``raw`` to ``shared`` channels, in the given order.

    Raises ``ValueError`` (fail loudly) if any requested channel is absent, listing
    the missing ones, so montage/audit mismatches never pass silently.
    """
    present = set(raw.ch_names)
    missing = [ch for ch in shared if ch not in present]
    if missing:
        raise ValueError(f"Recording is missing expected shared channels: {missing}")
    raw.pick(shared)
    raw.reorder_channels(shared)
    return raw


def set_standard_montage(raw: Any, montage: str = "standard_1005") -> Any:
    """Set a standard 10-05/10-20 montage, ignoring channels without positions."""
    import mne

    std = mne.channels.make_standard_montage(montage)
    raw.set_montage(std, match_case=False, on_missing="warn")
    return raw
