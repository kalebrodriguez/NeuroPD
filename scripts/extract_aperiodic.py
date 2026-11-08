"""Extract peak-separated aperiodic features for every cohort (ADR 0015).

For each participant: pool clean epochs across sessions, average the Welch PSD over
epochs per channel, fit spectral parameterization (fooof 1.1.1) and the ADR 0012
log-log line on the same spectra, and average channels within regions. Writes the
git-ignored ``data/processed/aperiodic_<cohort>.parquet``.

Usage:
    uv run python scripts/extract_aperiodic.py            # all cohorts
    uv run python scripts/extract_aperiodic.py ds004584
"""

from __future__ import annotations

import sys

import pandas as pd

from extract_features import (
    PROCESSED_ROOT,
    _epoch_files_by_participant,
    _group_map,
    _load_config,
    _load_pooled,
)
from neuropd.data.openneuro import DATASETS
from neuropd.features.specparam_features import SpecparamSettings, participant_aperiodic_row
from neuropd.logging import configure_logging


def run(accession: str) -> None:
    log = configure_logging()
    psd_cfg = _load_config(None).psd  # type: ignore[attr-defined]
    settings = SpecparamSettings.from_yaml()
    groups = _group_map(accession)
    rows = []
    for pid, paths in sorted(_epoch_files_by_participant(accession).items()):
        if pid not in groups:
            continue
        data, ch_names, sfreq = _load_pooled(paths)
        row = participant_aperiodic_row(data, sfreq, ch_names, psd_cfg, settings)
        rows.append({"participant_id": pid, "dataset": accession, "group": groups[pid], **row})
    frame = pd.DataFrame(rows)
    dest = PROCESSED_ROOT / f"aperiodic_{accession}.parquet"
    frame.to_parquet(dest, index=False)
    r2 = frame.filter(like="sp_r2__").to_numpy()
    log.info(
        "Wrote %s: %d participants; specparam r2 median %.3f, min %.3f",
        dest,
        len(frame),
        float(pd.Series(r2.ravel()).median()),
        float(r2.min()),
    )


def main(argv: list[str] | None = None) -> int:
    targets = list(sys.argv[1:] if argv is None else argv) or list(DATASETS)
    for accession in targets:
        run(accession)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
