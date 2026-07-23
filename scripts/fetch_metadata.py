"""Fetch **metadata-only** BIDS sidecars for the audit (Milestone 1).

Downloads only small ``*.json``/``*.tsv`` files (participants, channels, eeg
sidecars, coordinates, dataset descriptions, READMEs are fetched separately) into
``data/metadata/<accession>/``, which is git-ignored. It never downloads the
large binary recordings. To limit API load, ds007526 fetches only the
resting-state sidecars (the project's primary condition) and skips ``sourcedata``.

Usage:
    uv run python scripts/fetch_metadata.py [ds002778 ds007526]
"""

from __future__ import annotations

import sys
from pathlib import Path

from neuropd.data.openneuro import DATASETS, download_metadata
from neuropd.logging import configure_logging

METADATA_ROOT = Path("data/metadata")


def _rest_only(path: str) -> bool:
    # Keep dataset-level files and resting-state recordings; drop walking task.
    return "task-walk" not in path


def _skip_sourcedata(rel_dir: str) -> bool:
    top = rel_dir.split("/", 1)[0]
    return top != "sourcedata"


def fetch(accession: str) -> list[Path]:
    ref = DATASETS[accession]
    dest = METADATA_ROOT / accession
    path_filter = _rest_only if accession == "ds007526" else None
    written = download_metadata(
        ref.accession,
        ref.tag,
        dest,
        path_filter=path_filter,
        dir_filter=_skip_sourcedata,
    )
    return written


def main(argv: list[str] | None = None) -> int:
    log = configure_logging()
    argv = list(sys.argv[1:] if argv is None else argv)
    targets = argv or list(DATASETS)
    for accession in targets:
        if accession not in DATASETS:
            log.error("Unknown dataset: %s", accession)
            return 2
        log.info("Fetching metadata for %s ...", accession)
        written = fetch(accession)
        log.info("  wrote %d metadata files under data/metadata/%s", len(written), accession)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
