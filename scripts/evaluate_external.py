"""Frozen external-transfer evaluation (Milestone 5, spec Section 14.4).

Fits each frozen baseline on the ENTIRE development cohort and evaluates it ONCE on
the ENTIRE external cohort (default: train ds007526 -> test ds002778). Reports
external metrics with participant-level bootstrap CIs, the generalization gap
versus internal cross-validated performance, and calibration (Brier score) for
probability models. The reverse direction (ds002778 -> ds007526) is an optional,
separate experiment (``--bidirectional``).

The external cohort is never used for tuning; the pipeline and analysis plan are
frozen (ADRs 0005-0007). Results (git-ignored JSON) go to ``reports/tables/`` and a
committed Markdown summary to ``docs/external_transfer.md``.

Usage:
    uv run python scripts/evaluate_external.py                 # ds007526 -> ds002778
    uv run python scripts/evaluate_external.py --bidirectional
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from neuropd.data.demographics import load_demographics
from neuropd.evaluation.bootstrap import bootstrap_metric_cis
from neuropd.evaluation.metrics import classification_metrics
from neuropd.evaluation.transfer import evaluate_transfer, generalization_gap
from neuropd.features.matrix import feature_columns
from neuropd.logging import configure_logging
from neuropd.modeling.baselines import BASELINES, make_estimator
from neuropd.modeling.calibration import calibration_summary
from neuropd.modeling.pipeline import cross_validate_grouped

PROCESSED_ROOT = Path("data/processed")
TABLES_ROOT = Path("reports/tables")
REPORT = Path("docs/external_transfer.md")

METRIC_KEYS = ["balanced_accuracy", "roc_auc", "sensitivity", "specificity", "f1"]
PROBA_MODELS = {"demographics", "logreg", "random_forest"}  # expose predict_proba
SEED = 20240517
N_SPLITS, N_REPEATS, N_BOOT = 5, 5, 2000


def _load(accession: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, list[str]]:
    frame = pd.read_parquet(PROCESSED_ROOT / f"features_{accession}.parquet")
    y = (frame["group"].to_numpy() == "PD").astype(int)
    ids = frame["participant_id"].to_numpy()
    return frame, y, ids, feature_columns(frame)


def _features_for(name: str, frame: pd.DataFrame, fcols: list[str], accession: str) -> np.ndarray:
    if name == "demographics":
        return load_demographics(accession, list(frame["participant_id"]))
    return frame[fcols].to_numpy(dtype=float)


def _internal_point(name: str, x, y, ids) -> dict[str, float]:
    """Internal cross-validated point metrics on the training cohort (for the gap)."""
    cv = cross_validate_grouped(
        lambda: make_estimator(name, seed=SEED),
        x,
        y,
        ids,
        n_splits=N_SPLITS,
        n_repeats=N_REPEATS,
        seed=SEED,
    )
    return classification_metrics(cv.y_true, cv.y_pred, cv.y_score)


def run_direction(train_acc: str, test_acc: str, log) -> dict:
    tr_frame, y_tr, ids_tr, fcols_tr = _load(train_acc)
    te_frame, y_te, ids_te, fcols_te = _load(test_acc)
    if set(fcols_tr) != set(fcols_te):
        raise ValueError("feature columns differ between cohorts; re-extract with the same config")
    fcols = fcols_tr  # canonical order from the training cohort
    log.info(
        "Transfer %s -> %s: train n=%d (%d PD), test n=%d (%d PD), %d features",
        train_acc,
        test_acc,
        len(y_tr),
        int(y_tr.sum()),
        len(y_te),
        int(y_te.sum()),
        len(fcols),
    )

    results: dict[str, dict] = {}
    for name in BASELINES:
        x_tr = _features_for(name, tr_frame, fcols, train_acc)
        x_te = _features_for(name, te_frame[["participant_id", *fcols]], fcols, test_acc)
        res = evaluate_transfer(
            lambda n=name: make_estimator(n, seed=SEED),
            x_tr,
            y_tr,
            x_te,
            y_te,
            ids_te,
            train_dataset=train_acc,
            test_dataset=test_acc,
        )
        external = bootstrap_metric_cis(
            res.y_true, res.y_pred, res.y_score, n_boot=N_BOOT, seed=SEED
        )
        internal = _internal_point(name, x_tr, y_tr, ids_tr)
        ext_point = {k: external[k]["point"] for k in METRIC_KEYS}
        gap = generalization_gap(internal, ext_point)
        entry: dict = {
            "external": {k: external[k] for k in METRIC_KEYS},
            "internal_point": {k: internal[k] for k in METRIC_KEYS},
            "generalization_gap": gap,
        }
        if name in PROBA_MODELS:
            entry["calibration"] = calibration_summary(res.y_true, res.y_score, n_bins=5)
        results[name] = entry
        log.info(
            "%-13s ext bal_acc=%.3f AUC=%.3f | int bal_acc=%.3f AUC=%.3f | gap=%+.3f",
            name,
            ext_point["balanced_accuracy"],
            ext_point["roc_auc"],
            internal["balanced_accuracy"],
            internal["roc_auc"],
            gap["balanced_accuracy"],
        )

    return {
        "train_cohort": train_acc,
        "test_cohort": test_acc,
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "n_train": len(y_tr),
        "n_test": len(y_te),
        "n_features": len(fcols),
        "results": results,
    }


def _render(payloads: list[dict]) -> str:
    lines = [
        "# External Transfer Results",
        "",
        f"> Generated by `scripts/evaluate_external.py` on "
        f"{payloads[0]['generated_utc']} from the git-ignored feature matrices. Each "
        "model is fit on the FULL development cohort and evaluated ONCE on the FULL "
        "external cohort; the external cohort is never used for tuning (spec Section "
        "6.2). Intervals are 95% participant-level bootstrap CIs.",
        "",
    ]
    for p in payloads:
        lines += [
            f"## {p['train_cohort']} -> {p['test_cohort']}",
            "",
            f"Train n={p['n_train']}, test n={p['n_test']}, {p['n_features']} features. "
            "`gap` is internal (cross-validated) minus external balanced accuracy "
            "(positive = worse on the external cohort).",
            "",
            "| model | ext bal acc | ext ROC-AUC | int bal acc | gap (bal acc) | Brier |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for name, r in p["results"].items():
            ext_ba = r["external"]["balanced_accuracy"]
            ext_auc = r["external"]["roc_auc"]
            brier = f"{r['calibration']['brier']:.3f}" if "calibration" in r else "-"
            lines.append(
                f"| {name} "
                f"| {ext_ba['point']:.3f} [{ext_ba['lo']:.3f}, {ext_ba['hi']:.3f}] "
                f"| {ext_auc['point']:.3f} [{ext_auc['lo']:.3f}, {ext_auc['hi']:.3f}] "
                f"| {r['internal_point']['balanced_accuracy']:.3f} "
                f"| {r['generalization_gap']['balanced_accuracy']:+.3f} "
                f"| {brier} |"
            )
        lines.append("")
    lines += [
        "Interpretation: a large positive gap and near-chance external balanced "
        "accuracy would indicate that within-cohort separation does not transfer - "
        "the central hypothesis of this project (spec Section 3.1). Compare each EEG "
        "model against the demographics-only row; treat weak or null transfer as a "
        "valid, informative result, not a failure.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NeuroPD frozen external evaluation")
    parser.add_argument(
        "--bidirectional", action="store_true", help="Also run ds002778 -> ds007526."
    )
    args = parser.parse_args(argv)
    log = configure_logging()

    directions = [("ds007526", "ds002778")]
    if args.bidirectional:
        directions.append(("ds002778", "ds007526"))

    payloads = [run_direction(tr, te, log) for tr, te in directions]
    TABLES_ROOT.mkdir(parents=True, exist_ok=True)
    for p in payloads:
        dest = TABLES_ROOT / f"external_{p['train_cohort']}_to_{p['test_cohort']}.json"
        dest.write_text(json.dumps(p, indent=2))
    REPORT.write_text(_render(payloads))
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
