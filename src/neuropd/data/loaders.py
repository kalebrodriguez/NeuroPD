"""Raw recording loaders (scaffold).

Wraps MNE readers to load resting-state recordings into a standard in-memory
representation while keeping raw files immutable (spec Section 5.2). No logic is
present during Milestone 0; readers are added in the preprocessing milestone
against real, inspected files.
"""

from __future__ import annotations

from pathlib import Path

_NOT_IMPLEMENTED = "Implemented in Milestone 2 (preprocessing) against real recordings."


def load_raw(path: str | Path):
    """Load a single raw recording into an ``mne.io.Raw`` (not yet implemented)."""
    raise NotImplementedError(_NOT_IMPLEMENTED)
