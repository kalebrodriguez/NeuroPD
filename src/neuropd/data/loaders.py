"""Raw recording discovery and loading.

Enumerates resting-state recordings from a local BIDS dataset under ``data/raw/``
and loads them with the appropriate MNE reader, keeping raw files immutable
(spec Section 5.2). Group labels come from each dataset's ``participants.tsv``
(explicit ``group`` column when present, else the ds002778 id prefix).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neuropd.data.audit import participant_group, read_tsv

_READERS = {".bdf": "read_raw_bdf", ".set": "read_raw_eeglab", ".edf": "read_raw_edf"}


@dataclass(frozen=True)
class Recording:
    """A single resting-state recording on disk."""

    dataset: str
    participant_id: str
    group: str
    session: str | None
    task: str
    path: Path


def _group_map(dataset_root: Path) -> dict[str, str]:
    participants = read_tsv(dataset_root / "participants.tsv")
    out: dict[str, str] = {}
    for row in participants:
        pid = row.get("participant_id", "")
        g = participant_group(pid, row.get("group"))
        if g is not None:
            out[pid] = g
    return out


def _parse_entities(filename: str) -> dict[str, str]:
    """Parse BIDS ``key-value`` entities from a filename stem."""
    out: dict[str, str] = {}
    for token in filename.split("_"):
        if "-" in token:
            key, _, value = token.partition("-")
            out[key] = value
    return out


def iter_recordings(accession: str, raw_root: Path, *, task: str = "rest") -> Iterator[Recording]:
    """Yield resting-state recordings for a dataset, in sorted participant order.

    Raises ``FileNotFoundError`` if the dataset is not present under ``raw_root``.
    """
    dataset_root = raw_root / accession
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"Dataset not found: {dataset_root} (download it first).")
    groups = _group_map(dataset_root)
    paths = sorted(
        p for suffix in _READERS for p in dataset_root.rglob(f"*_task-{task}_eeg{suffix}")
    )
    for path in paths:
        ents = _parse_entities(path.stem)
        pid = f"sub-{ents.get('sub', '')}"
        group = groups.get(pid)
        if group is None:
            continue  # participant without a resolvable group label; skip loudly upstream
        yield Recording(
            dataset=accession,
            participant_id=pid,
            group=group,
            session=ents.get("ses"),
            task=ents.get("task", task),
            path=path,
        )


def load_raw(path: str | Path, *, preload: bool = True) -> Any:
    """Load a raw recording, choosing the MNE reader from the file extension."""
    import mne

    p = Path(path)
    reader_name = _READERS.get(p.suffix.lower())
    if reader_name is None:
        raise ValueError(f"Unsupported recording format: {p.suffix}")
    reader = getattr(mne.io, reader_name)
    return reader(p, preload=preload, verbose="ERROR")
