"""Pre-registered confirmatory transfer to new held-out cohorts (ADR 0013).

Runs exactly the frozen plan in ``docs/decisions/0013-confirmatory-third-cohorts.md``:

* **H1 (primary):** logreg on the relative-band-power family, fit on the FULL
  ds007526 cohort, evaluated ONCE on the FULL confirmatory cohort. Confirmed if the
  95% participant-level bootstrap CI lower bound of ROC-AUC exceeds 0.50.
* **Secondary (descriptive):** all-feature baselines, the other feature families,
  and dataset-identity separability (ds007526 vs the new cohort).

Nothing is tuned on the confirmatory cohort. Each cohort is written to its own
git-ignored JSON (``reports/tables/confirmatory_<cohort>.json``). The committed
report ``docs/confirmatory_transfer.md`` is re-rendered from every JSON present, so
cohorts can be added one at a time.

Usage:
    uv run python scripts/evaluate_confirmatory.py ds004584
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
from neuropd.evaluation.transfer import evaluate_transfer
from neuropd.features.families import FAMILIES, PRIMARY_FAMILY, family_columns
from neuropd.features.matrix import feature_columns
from neuropd.logging import configure_logging
from neuropd.modeling.baselines import BASELINES, make_estimator
from neuropd.modeling.calibration import calibration_summary
from neuropd.modeling.pipeline import cross_validate_grouped

PROCESSED_ROOT = Path("data/processed")
TABLES_ROOT = Path("reports/tables")
REPORT = Path("docs/confirmatory_transfer.md")
DEV = "ds007526"
CONFIRMATORY = ("ds004584", "ds003490")
SEED, N_BOOT = 20240517, 2000
H1_THRESHOLD = 0.5
PROBA_MODELS = {"demographics", "logreg", "random_forest"}
METRIC_KEYS = ["balanced_accuracy", "roc_auc", "sensitivity", "specificity", "f1"]


def h1_confirmed(auc_ci_lo: float) -> bool:
    """Pre-registered decision rule: the AUC 95% CI lower bound exceeds 0.50."""
    return bool(auc_ci_lo > H1_THRESHOLD)


def _load(accession: str) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    frame = pd.read_parquet(PROCESSED_ROOT / f"features_{accession}.parquet")
    y = (frame["group"].to_numpy() == "PD").astype(int)
    return frame, y, frame["participant_id"].to_numpy()


def _transfer(model: str, x_tr, y_tr, x_te, y_te, ids_te, test: str) -> dict:
    res = evaluate_transfer(
        lambda: make_estimator(model, seed=SEED),
        x_tr,
        y_tr,
        x_te,
        y_te,
        ids_te,
        train_dataset=DEV,
        test_dataset=test,
    )
    out: dict = {
        "external": {
            k: v
            for k, v in bootstrap_metric_cis(
                res.y_true, res.y_pred, res.y_score, n_boot=N_BOOT, seed=SEED
            ).items()
            if k in METRIC_KEYS
        }
    }
    if model in PROBA_MODELS:
        out["calibration"] = calibration_summary(res.y_true, res.y_score, n_bins=5)
    return out


def run_cohort(test: str, log) -> dict:
    dev, y_dev, _ids_dev = _load(DEV)
    tst, y_tst, ids_tst = _load(test)
    cols = feature_columns(dev)
    if set(cols) != set(feature_columns(tst)):
        raise ValueError("feature columns differ; re-extract both cohorts with the same config")
    log.info(
        "Confirmatory %s -> %s: train n=%d (%d PD), test n=%d (%d PD), %d features",
        DEV,
        test,
        len(y_dev),
        int(y_dev.sum()),
        len(y_tst),
        int(y_tst.sum()),
        len(cols),
    )

    # Primary: H1 (relative power, logreg).
    pcols = family_columns(cols, PRIMARY_FAMILY)
    primary = _transfer(
        "logreg",
        dev[pcols].to_numpy(dtype=float),
        y_dev,
        tst[pcols].to_numpy(dtype=float),
        y_tst,
        ids_tst,
        test,
    )
    auc = primary["external"]["roc_auc"]
    primary.update(
        {
            "family": PRIMARY_FAMILY,
            "model": "logreg",
            "n_features": len(pcols),
            "confirmed": h1_confirmed(auc["lo"]),
        }
    )
    log.info(
        "H1 %s: AUC %.3f [%.3f, %.3f] -> %s",
        test,
        auc["point"],
        auc["lo"],
        auc["hi"],
        "CONFIRMED" if primary["confirmed"] else "not confirmed",
    )

    # Secondary 1: all-feature baselines (+ majority, demographics-only).
    baselines: dict[str, dict] = {}
    x_dev_all, x_tst_all = dev[cols].to_numpy(dtype=float), tst[cols].to_numpy(dtype=float)
    demo_dev = load_demographics(DEV, list(dev["participant_id"]))
    demo_tst = load_demographics(test, list(tst["participant_id"]))
    for name in BASELINES:
        x_tr, x_te = (demo_dev, demo_tst) if name == "demographics" else (x_dev_all, x_tst_all)
        baselines[name] = _transfer(name, x_tr, y_dev, x_te, y_tst, ids_tst, test)

    # Secondary 2: every feature family (logreg).
    families: dict[str, dict] = {}
    for fam in FAMILIES:
        fcols = family_columns(cols, fam)
        families[fam] = _transfer(
            "logreg",
            dev[fcols].to_numpy(dtype=float),
            y_dev,
            tst[fcols].to_numpy(dtype=float),
            y_tst,
            ids_tst,
            test,
        )
        families[fam]["n_features"] = len(fcols)

    # Secondary 3: dataset-identity separability (ds007526 vs the new cohort).
    x_site = np.vstack([x_dev_all, x_tst_all])
    y_site = np.array([1] * len(x_dev_all) + [0] * len(x_tst_all))
    groups = np.array(
        [f"{DEV}:{i}" for i in dev["participant_id"]] + [f"{test}:{i}" for i in ids_tst]
    )
    identity: dict[str, dict[str, float]] = {}
    for name in ("logreg", "random_forest"):
        cv = cross_validate_grouped(
            lambda n=name: make_estimator(n, seed=SEED),
            x_site,
            y_site,
            groups,
            n_splits=5,
            n_repeats=5,
            seed=SEED,
        )
        m = classification_metrics(cv.y_true, cv.y_pred, cv.y_score)
        identity[name] = {"balanced_accuracy": m["balanced_accuracy"], "roc_auc": m["roc_auc"]}

    return {
        "adr": "0013",
        "train_cohort": DEV,
        "test_cohort": test,
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "n_train": len(y_dev),
        "n_test": len(y_tst),
        "n_test_pd": int(y_tst.sum()),
        "n_features": len(cols),
        "primary": primary,
        "baselines": baselines,
        "families": families,
        "dataset_identity": identity,
    }


def _ci(m: dict[str, float]) -> str:
    return f"{m['point']:.3f} [{m['lo']:.3f}, {m['hi']:.3f}]"


def render(payloads: list[dict]) -> str:
    lines = [
        "# Confirmatory Transfer (pre-registered, ADR 0013)",
        "",
        "> Generated by `scripts/evaluate_confirmatory.py` from the git-ignored feature "
        "matrices. Each model is fit on the FULL ds007526 cohort and evaluated ONCE on "
        "the FULL confirmatory cohort; nothing is tuned on it. Intervals are 95% "
        "participant-level bootstrap CIs (2,000 resamples). The plan was committed "
        "before the cohorts were downloaded (ADR 0013).",
        "",
        "**H1:** logreg on relative band power transfers above chance (AUC 95% CI lower "
        "bound > 0.50). The exploratory estimate on ds002778 was AUC 0.867 (n=30, "
        "ADR 0010).",
        "",
        "| cohort | n (PD) | H1 external AUC | bal acc | verdict |",
        "| --- | --- | --- | --- | --- |",
    ]
    for p in payloads:
        pr = p["primary"]["external"]
        verdict = "**confirmed**" if p["primary"]["confirmed"] else "**not confirmed**"
        lines.append(
            f"| {p['test_cohort']} | {p['n_test']} ({p['n_test_pd']}) | {_ci(pr['roc_auc'])} "
            f"| {_ci(pr['balanced_accuracy'])} | {verdict} |"
        )
    lines.append("")
    for p in payloads:
        lines += [
            f"## {p['train_cohort']} -> {p['test_cohort']}",
            "",
            f"Train n={p['n_train']}, test n={p['n_test']} ({p['n_test_pd']} PD), "
            f"{p['n_features']} features. Generated {p['generated_utc']}.",
            "",
            "### Secondary: all-feature baselines",
            "",
            "| model | ext bal acc | ext ROC-AUC | Brier |",
            "| --- | --- | --- | --- |",
        ]
        for name, r in p["baselines"].items():
            brier = f"{r['calibration']['brier']:.3f}" if "calibration" in r else "-"
            lines.append(
                f"| {name} | {_ci(r['external']['balanced_accuracy'])} "
                f"| {_ci(r['external']['roc_auc'])} | {brier} |"
            )
        lines += [
            "",
            "### Secondary: feature families (logreg)",
            "",
            "| family | n | ext bal acc | ext ROC-AUC |",
            "| --- | --- | --- | --- |",
        ]
        for fam, r in p["families"].items():
            lines.append(
                f"| {fam} | {r['n_features']} | {_ci(r['external']['balanced_accuracy'])} "
                f"| {_ci(r['external']['roc_auc'])} |"
            )
        lines += [
            "",
            f"### Secondary: dataset identity ({p['train_cohort']} vs {p['test_cohort']})",
            "",
            "| model | bal acc | ROC-AUC |",
            "| --- | --- | --- |",
        ]
        for name, m in p["dataset_identity"].items():
            lines.append(f"| {name} | {m['balanced_accuracy']:.3f} | {m['roc_auc']:.3f} |")
        lines.append("")
    lines += [
        "Research tool only: these are group-level transfer estimates, not a "
        "diagnostic test. Interpretation is recorded in ADR 0013 and "
        "`docs/research_log.md`.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NeuroPD confirmatory transfer (ADR 0013)")
    parser.add_argument("cohort", choices=CONFIRMATORY)
    args = parser.parse_args(argv)
    log = configure_logging()
    payload = run_cohort(args.cohort, log)
    TABLES_ROOT.mkdir(parents=True, exist_ok=True)
    (TABLES_ROOT / f"confirmatory_{args.cohort}.json").write_text(json.dumps(payload, indent=2))
    payloads = [
        json.loads(path.read_text())
        for c in CONFIRMATORY
        if (path := TABLES_ROOT / f"confirmatory_{c}.json").is_file()
    ]
    REPORT.write_text(render(payloads))
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
