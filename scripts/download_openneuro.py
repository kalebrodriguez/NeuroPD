"""Download raw OpenNeuro datasets into ``data/raw/`` (Milestone 2).

APPROVAL-GATED (spec Section 29.7): only run after the project owner approves the
download sizes and licenses. Raw data are written under ``data/raw/<accession>/``
(git-ignored) and then made read-only to keep them immutable (spec Section 5.2).

To limit footprint, ds007526 downloads only the resting-state task (the project's
primary condition) and skips ``sourcedata``; ds002778 is small and fetched in full.
After download, per-file SHA-256 checksums are written and a committed provenance
summary is updated (``docs/data_provenance.md``).

Usage:
    uv run python scripts/download_openneuro.py [ds002778 ds007526]
"""

from __future__ import annotations

import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path

from neuropd.data.openneuro import DATASETS, download_dataset, sha256_file
from neuropd.logging import configure_logging

RAW_ROOT = Path("data/raw")
PROVENANCE_DOC = Path("docs/data_provenance.md")

# Verified download sizes/licenses (see docs/dataset_audit.md).
SIZES = {"ds002778": "~545 MiB", "ds007526": "~4.27 GiB (rest-only subset is smaller)"}


def _rest_only(path: str) -> bool:
    return "task-walk" not in path


def _skip_sourcedata(rel_dir: str) -> bool:
    return rel_dir.split("/", 1)[0] != "sourcedata"


# Bookkeeping files kept writable and excluded from checksums.
_BOOKKEEPING = {"checksums.sha256", "download_info.json"}


def _make_readonly(root: Path) -> None:
    for p in root.rglob("*"):
        if p.is_file() and p.name not in _BOOKKEEPING:
            p.chmod(p.stat().st_mode & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH)


def _data_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.name not in _BOOKKEEPING)


def _write_checksums(root: Path) -> tuple[int, int]:
    """Write a checksums.sha256 manifest; return (n_files, total_bytes)."""
    files = _data_files(root)
    lines = []
    total = 0
    for p in files:
        total += p.stat().st_size
        lines.append(f"{sha256_file(p)}  {p.relative_to(root).as_posix()}")
    cs = root / "checksums.sha256"
    if cs.exists():
        cs.chmod(0o644)
    cs.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(files), total


def download(accession: str) -> None:
    ref = DATASETS[accession]
    dest = RAW_ROOT / accession
    path_filter = _rest_only if accession == "ds007526" else None
    download_dataset(
        ref.accession, ref.tag, dest, path_filter=path_filter, dir_filter=_skip_sourcedata
    )
    _write_checksums(dest)
    (dest / "download_info.json").write_text(
        json.dumps({"accession": accession, "tag": ref.tag, "retrieved_utc": _now()}, indent=2),
        encoding="utf-8",
    )
    _make_readonly(dest)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _scan(accession: str) -> dict[str, object] | None:
    """Build a provenance record for a dataset from disk state (idempotent)."""
    root = RAW_ROOT / accession
    if not root.is_dir():
        return None
    files = _data_files(root)
    info_path = root / "download_info.json"
    info = json.loads(info_path.read_text()) if info_path.exists() else {}
    return {
        "accession": accession,
        "tag": info.get("tag", DATASETS[accession].tag),
        "n_files": len(files),
        "total_bytes": sum(p.stat().st_size for p in files),
        "retrieved_utc": info.get("retrieved_utc", "unknown"),
    }


def _update_provenance() -> None:
    """Regenerate the committed provenance summary from all downloaded datasets."""
    records = [r for acc in DATASETS if (r := _scan(acc)) is not None]
    lines = ["# Data Provenance\n"]
    lines.append(
        "Raw datasets downloaded into `data/raw/` (git-ignored, immutable/read-only). "
        "Per-file SHA-256 checksums are in each dataset's `checksums.sha256`. This file "
        "records the committed summary (spec Section 7). Regenerate with "
        "`uv run python scripts/download_openneuro.py --provenance-only`.\n"
    )
    for r in records:
        mib = int(r["total_bytes"]) / 1024 / 1024
        lines.append(f"## {r['accession']} (snapshot {r['tag']})\n")
        lines.append(f"- Files: {r['n_files']}")
        lines.append(f"- Total size: {mib:.1f} MiB")
        lines.append(f"- Retrieved (UTC): {r['retrieved_utc']}")
        lines.append(f"- Approx. published size: {SIZES.get(str(r['accession']), 'n/a')}")
        lines.append("")
    PROVENANCE_DOC.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    log = configure_logging()
    if os.environ.get("NEUROPD_ALLOW_DOWNLOAD", "1") != "1":
        log.error("Download disabled (NEUROPD_ALLOW_DOWNLOAD != 1).")
        return 2
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--provenance-only" in argv:
        _update_provenance()
        log.info("Regenerated %s from disk", PROVENANCE_DOC)
        return 0
    targets = argv or list(DATASETS)
    for accession in targets:
        if accession not in DATASETS:
            log.error("Unknown dataset: %s", accession)
            return 2
        log.info("Downloading %s (%s) ...", accession, SIZES.get(accession, "?"))
        download(accession)
    _update_provenance()
    log.info("Wrote %s", PROVENANCE_DOC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
