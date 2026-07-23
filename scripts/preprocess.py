"""Run the configurable preprocessing pipeline on downloaded recordings (Milestone 2).

Loads the shared-channel harmonization config and a preprocessing profile, then
preprocesses resting-state recordings into clean epochs with QC. Clean epochs are
saved under ``data/processed/`` (git-ignored) and a QC table is written to
``reports/tables/`` (git-ignored). Raw data are never modified.

Examples:
    # 2 participants per group from each dataset, end-to-end, with a QC figure:
    uv run python scripts/preprocess.py --limit-per-group 2 --figures
    # full run on one dataset:
    uv run python scripts/preprocess.py --dataset ds002778 --limit-per-group 0
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from neuropd.config import load_preprocessing_config, load_yaml
from neuropd.data.loaders import Recording, iter_recordings, load_raw
from neuropd.data.openneuro import DATASETS
from neuropd.logging import configure_logging
from neuropd.preprocessing.pipeline import preprocess_raw
from neuropd.preprocessing.quality import QCResult, qc_table

RAW_ROOT = Path("data/raw")
PROCESSED_ROOT = Path("data/processed")
TABLES_ROOT = Path("reports/tables")
FIGURES_ROOT = Path("reports/figures")
HARMONIZATION = Path("configs/harmonization.yaml")
PROFILES = {
    "conservative": Path("configs/preprocessing/conservative.yaml"),
    "sensitivity": Path("configs/preprocessing/sensitivity.yaml"),
}


def _line_freq(accession: str) -> float:
    cfg = load_yaml(Path("configs/data") / f"{accession}.yaml")
    return float(cfg["verified"]["line_frequency_hz"])


def _select(recordings: list[Recording], limit_per_group: int) -> list[Recording]:
    if limit_per_group <= 0:
        return recordings
    counts: dict[str, int] = {}
    out: list[Recording] = []
    for r in recordings:
        if counts.get(r.group, 0) < limit_per_group:
            out.append(r)
            counts[r.group] = counts.get(r.group, 0) + 1
    return out


def _save_epochs(epochs: object, rec: Recording) -> Path:
    stem = rec.participant_id + (f"_{rec.session}" if rec.session else "")
    dest = PROCESSED_ROOT / rec.dataset / f"{stem}_task-{rec.task}_epo.fif"
    dest.parent.mkdir(parents=True, exist_ok=True)
    epochs.save(dest, overwrite=True, verbose="ERROR")  # type: ignore[attr-defined]
    return dest


def _write_qc(rows: list[dict[str, object]], accession: str) -> Path:
    TABLES_ROOT.mkdir(parents=True, exist_ok=True)
    dest = TABLES_ROOT / f"preprocessing_qc_{accession}.csv"
    if rows:
        with dest.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    return dest


def _save_psd_figure(epochs: object, rec: Recording) -> Path | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    FIGURES_ROOT.mkdir(parents=True, exist_ok=True)
    fig = epochs.compute_psd(fmax=45.0, verbose="ERROR").plot(show=False)  # type: ignore[attr-defined]
    dest = FIGURES_ROOT / f"psd_{rec.dataset}_{rec.participant_id}.png"
    fig.savefig(dest, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return dest


def run_dataset(accession: str, cfg_path: Path, limit_per_group: int, *, save: bool, figures: bool):
    log = configure_logging()
    cfg = load_preprocessing_config(cfg_path)
    shared = list(load_yaml(HARMONIZATION)["shared_channels"])
    line_freq = _line_freq(accession)
    recordings = _select(list(iter_recordings(accession, RAW_ROOT)), limit_per_group)
    log.info(
        "Preprocessing %d recordings from %s (line=%g Hz)",
        len(recordings),
        accession,
        line_freq,
    )

    results: list[QCResult] = []
    first_fig_done = False
    for rec in recordings:
        raw = load_raw(rec.path)
        res = preprocess_raw(raw, cfg, line_freq=line_freq, shared_channels=shared, recording=rec)
        results.append(res.qc)
        if save and not res.qc.excluded:
            _save_epochs(res.epochs, rec)
        if figures and not first_fig_done and not res.qc.excluded:
            path = _save_psd_figure(res.epochs, rec)
            if path is not None:
                log.info("Wrote QC figure %s", path)
            first_fig_done = True

    rows = qc_table(results)
    dest = _write_qc(rows, accession)
    n_excl = sum(1 for r in results if r.excluded)
    log.info("QC written to %s (%d recordings, %d excluded)", dest, len(results), n_excl)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NeuroPD preprocessing")
    parser.add_argument("--dataset", default="all", choices=[*DATASETS, "all"])
    parser.add_argument("--profile", default="conservative", choices=list(PROFILES))
    parser.add_argument(
        "--limit-per-group",
        type=int,
        default=2,
        help="Max recordings per group per dataset (0 = all).",
    )
    parser.add_argument("--no-save", action="store_true", help="Do not save processed epochs.")
    parser.add_argument("--figures", action="store_true", help="Save a QC PSD figure per dataset.")
    args = parser.parse_args(argv)

    cfg_path = PROFILES[args.profile]
    targets = list(DATASETS) if args.dataset == "all" else [args.dataset]
    for accession in targets:
        run_dataset(
            accession,
            cfg_path,
            args.limit_per_group,
            save=not args.no_save,
            figures=args.figures,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
