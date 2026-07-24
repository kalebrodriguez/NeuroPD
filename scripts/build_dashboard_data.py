"""Build committed, de-identified dashboard data (Milestone 7, spec Section 17).

The dashboard must run without raw EEG and use only derived, non-identifiable
results. This script reads the local (git-ignored) feature matrices and result
JSONs and writes small, committed artifacts to ``dashboard/data/``:

* ``metrics.json``   — internal, external, and dataset-shift metrics (aggregate).
* ``cohorts.json``   — per-cohort counts, group balance, and age/sex summaries.
* ``biomarkers.csv`` — per-participant values of a few interpretable features,
  labelled by dataset and group, with **no participant identifier** (anonymized).

Participant ids are dropped; only de-identified derived features remain. Run after
``train.py``, ``evaluate_external.py``, and ``explain.py``.

Usage:
    uv run python scripts/build_dashboard_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from neuropd.data.demographics import load_demographics
from neuropd.features.matrix import feature_columns

PROCESSED_ROOT = Path("data/processed")
TABLES_ROOT = Path("reports/tables")
OUT = Path("dashboard/data")
COHORTS = ("ds007526", "ds002778")

# Interpretable biomarkers surfaced in the dashboard (median over epochs).
BIOMARKERS = [
    "paf__occipital__median",
    "theta_alpha_ratio__central__median",
    "rel_power_alpha__occipital__median",
    "rel_power_theta__frontal__median",
    "rel_power_beta__occipital__median",
    "spectral_entropy__occipital__median",
    "hjorth_complexity__occipital__median",
]


def _read_json(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.is_file() else None


def build_cohorts() -> dict:
    cohorts = {}
    for acc in COHORTS:
        frame = pd.read_parquet(PROCESSED_ROOT / f"features_{acc}.parquet")
        demo = load_demographics(acc, list(frame["participant_id"]))
        age, sex_male = demo[:, 0], demo[:, 1]
        cohorts[acc] = {
            "n_participants": len(frame),
            "n_pd": int((frame["group"] == "PD").sum()),
            "n_hc": int((frame["group"] == "HC").sum()),
            "n_features": len(feature_columns(frame)),
            "age_mean": float(np.nanmean(age)),
            "age_min": float(np.nanmin(age)),
            "age_max": float(np.nanmax(age)),
            "pct_male": float(np.nanmean(sex_male) * 100),
        }
    return cohorts


def build_biomarkers() -> pd.DataFrame:
    frames = []
    for acc in COHORTS:
        frame = pd.read_parquet(PROCESSED_ROOT / f"features_{acc}.parquet")
        cols = [c for c in BIOMARKERS if c in frame.columns]
        sub = frame[["dataset", "group", *cols]].copy()  # NOTE: no participant_id
        frames.append(sub)
    return pd.concat(frames, ignore_index=True)


def build_metrics() -> dict:
    return {
        "internal_ds007526": _read_json(TABLES_ROOT / "internal_baselines_ds007526.json"),
        "external_a_to_b": _read_json(TABLES_ROOT / "external_ds007526_to_ds002778.json"),
        "external_b_to_a": _read_json(TABLES_ROOT / "external_ds002778_to_ds007526.json"),
        "dataset_shift": _read_json(TABLES_ROOT / "dataset_shift.json"),
    }


def _copy_if_present(name: str) -> None:
    src = TABLES_ROOT / name
    if src.is_file():
        (OUT / name).write_text(src.read_text())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cohorts.json").write_text(json.dumps(build_cohorts(), indent=2))
    (OUT / "metrics.json").write_text(json.dumps(build_metrics(), indent=2))
    bio = build_biomarkers()
    bio.to_csv(OUT / "biomarkers.csv", index=False)
    # Bundle the sensitivity + feature-importance summaries for the site (if present).
    _copy_if_present("sensitivity.json")
    _copy_if_present("feature_importance.json")
    print(f"Wrote dashboard data to {OUT}/ ({len(bio)} biomarker rows, no participant ids)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
