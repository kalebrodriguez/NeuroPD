"""BIDS dataset discovery helpers (scaffold).

Both target datasets are distributed in BIDS format on OpenNeuro
(``ds002778`` and ``ds007526``). This module will wrap :mod:`mne_bids` to
enumerate participants, sessions, tasks, and recording sidecars from the *real*
files on disk. It deliberately contains no logic during Milestone 0 so that no
dataset field, channel name, or parameter is ever assumed before inspection
(spec Section 1).

Planned public functions
------------------------
* ``list_subjects(bids_root)`` -> participant identifiers actually present.
* ``list_recordings(bids_root, task)`` -> per-recording BIDS paths.
* ``read_sidecar(bids_path)`` -> validated recording metadata (e.g. eye
  condition, sampling frequency, reference).
"""

from __future__ import annotations

from pathlib import Path

_NOT_IMPLEMENTED = "Implemented in Milestone 1 (dataset audit) once real BIDS files are available."


def list_subjects(bids_root: str | Path) -> list[str]:
    """Return participant identifiers present under a BIDS root (not yet implemented)."""
    raise NotImplementedError(_NOT_IMPLEMENTED)
