"""Extract interpretable, participant-level features (Milestone 3, spec Section 12).

Reads clean epochs produced by ``scripts/preprocess.py`` from ``data/processed/``,
computes interpretable spectral + complexity features per epoch and channel, and
aggregates them to ONE feature vector per participant (sessions pooled;
region-level spatial harmonization by default). Writes a git-ignored feature
matrix to ``data/processed/features_<accession>.parquet`` and a small, committed
provenance summary. Raw and processed EEG are never modified.

Examples:
    uv run python scripts/extract_features.py                 # all datasets
    uv run python scripts/extract_features.py --dataset ds002778
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from neuropd.config import load_feature_config, load_yaml
from neuropd.data.audit import participant_group, read_tsv
from neuropd.data.openneuro import DATASETS
from neuropd.features import aggregate as agg
from neuropd.features.matrix import ParticipantRecord, build_feature_frame, feature_columns
from neuropd.logging import configure_logging

RAW_ROOT = Path("data/raw")
PROCESSED_ROOT = Path("data/processed")
FEATURE_CONFIG = Path("configs/features/interpretable.yaml")
PROVENANCE = Path("data/metadata/feature_extraction_info.json")


def _group_map(accession: str) -> dict[str, str]:
    rows = read_tsv(RAW_ROOT / accession / "participants.tsv")
    out: dict[str, str] = {}
    for row in rows:
        pid = row.get("participant_id", "")
        g = participant_group(pid, row.get("group"))
        if g is not None:
            out[pid] = g
    return out


def _epoch_files_by_participant(accession: str) -> dict[str, list[Path]]:
    root = PROCESSED_ROOT / accession
    if not root.is_dir():
        raise FileNotFoundError(f"No processed epochs under {root}; run preprocess.py first.")
    by_pid: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(root.glob("*_epo.fif")):
        pid = path.name.split("_", 1)[0]  # e.g. "sub-pd11"
        by_pid[pid].append(path)
    return dict(by_pid)


def _load_pooled(paths: list[Path]) -> tuple[np.ndarray, list[str], float]:
    """Load and pool epochs across a participant's sessions into one array."""
    import mne

    arrays: list[np.ndarray] = []
    ref_names: list[str] | None = None
    ref_sfreq: float | None = None
    for p in paths:
        epochs = mne.read_epochs(p, preload=True, verbose="ERROR")
        names = list(epochs.ch_names)
        sfreq = float(epochs.info["sfreq"])
        if ref_names is None:
            ref_names, ref_sfreq = names, sfreq
        elif names != ref_names or abs(sfreq - ref_sfreq) > 1e-6:  # type: ignore[arg-type]
            raise ValueError(f"Inconsistent channels/sfreq across sessions for {p.name}")
        arrays.append(epochs.get_data(copy=False))
    assert ref_names is not None and ref_sfreq is not None
    return np.concatenate(arrays, axis=0), ref_names, ref_sfreq


def run_dataset(accession: str) -> Path:
    log = configure_logging()
    cfg = load_feature_config(FEATURE_CONFIG)
    shared = list(load_yaml(Path("configs/harmonization.yaml"))["shared_channels"])
    groups = _group_map(accession)
    by_pid = _epoch_files_by_participant(accession)
    log.info("Extracting features for %s: %d participants", accession, len(by_pid))

    records: list[ParticipantRecord] = []
    for pid, paths in sorted(by_pid.items()):
        group = groups.get(pid)
        if group is None:
            log.warning("Skipping %s (no group label)", pid)
            continue
        data, ch_names, sfreq = _load_pooled(paths)
        if ch_names != shared:
            log.warning("%s channel order differs from harmonization set", pid)
        feats = agg.participant_feature_row(data, sfreq, ch_names, cfg)
        records.append(
            ParticipantRecord(
                participant_id=pid,
                dataset=accession,
                group=group,
                n_sessions=len(paths),
                n_epochs=int(data.shape[0]),
                features=feats,
            )
        )
        log.info("%s: %s, %d sessions, %d pooled epochs", pid, group, len(paths), data.shape[0])

    frame = build_feature_frame(records)
    fcols = feature_columns(frame)
    n_missing = int(frame[fcols].isna().sum().sum())
    dest = PROCESSED_ROOT / f"features_{accession}.parquet"
    frame.to_parquet(dest, index=False)
    log.info(
        "Wrote %s: %d participants x %d features (%d NaN cells)",
        dest,
        len(frame),
        len(fcols),
        n_missing,
    )
    _update_provenance(accession, frame, fcols, n_missing, cfg.spatial)
    return dest


def _update_provenance(accession, frame, fcols, n_missing, spatial) -> None:
    PROVENANCE.parent.mkdir(parents=True, exist_ok=True)
    info = {}
    if PROVENANCE.exists():
        info = json.loads(PROVENANCE.read_text())
    counts = frame["group"].value_counts().to_dict()
    info[accession] = {
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "n_participants": len(frame),
        "group_counts": {str(k): int(v) for k, v in counts.items()},
        "n_features": len(fcols),
        "n_nan_cells": n_missing,
        "spatial": spatial,
    }
    PROVENANCE.write_text(json.dumps(info, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NeuroPD feature extraction")
    parser.add_argument("--dataset", default="all", choices=[*DATASETS, "all"])
    args = parser.parse_args(argv)
    targets = list(DATASETS) if args.dataset == "all" else [args.dataset]
    for accession in targets:
        run_dataset(accession)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
