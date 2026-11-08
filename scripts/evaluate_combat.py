"""Pre-declared ComBat harmonization analysis (ADR 0014).

For each external cohort (ds002778, ds004584, ds003490), fits each EEG model on the
FULL ds007526 cohort and evaluates it ONCE on the external cohort, after each
harmonizer: ``none``, ``per_cohort_zscore``, ``combat``, ``combat_agesex``.
Harmonizers use only the unlabeled features (and age/sex for ``combat_agesex``) of
both cohorts. Also reports dataset-identity separability after harmonization.

Writes ``reports/tables/combat.json`` (git-ignored) and ``docs/combat.md``.

Usage:
    uv run python scripts/evaluate_combat.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from neuropd.data.demographics import load_demographics
from neuropd.evaluation.bootstrap import bootstrap_metric_cis
from neuropd.evaluation.metrics import classification_metrics
from neuropd.evaluation.transfer import evaluate_transfer
from neuropd.features.families import PRIMARY_FAMILY, family_columns
from neuropd.features.matrix import feature_columns
from neuropd.logging import configure_logging
from neuropd.modeling.baselines import make_estimator
from neuropd.modeling.harmonization import apply_harmonization
from neuropd.modeling.pipeline import cross_validate_grouped

PROCESSED_ROOT = Path("data/processed")
TABLES_ROOT = Path("reports/tables")
REPORT = Path("docs/combat.md")
DEV = "ds007526"
EXTERNAL = ("ds002778", "ds004584", "ds003490")
METHODS = ("none", "per_cohort_zscore", "combat", "combat_agesex")
# (label, model, feature family or None for all features)
MODELS = (
    ("logreg", "logreg", None),
    ("svm_linear", "svm_linear", None),
    ("random_forest", "random_forest", None),
    ("logreg (relative power)", "logreg", PRIMARY_FAMILY),
)
PRIMARY = "logreg"
SEED, N_BOOT = 20240517, 2000


def _load(accession: str):
    frame = pd.read_parquet(PROCESSED_ROOT / f"features_{accession}.parquet")
    y = (frame["group"].to_numpy() == "PD").astype(int)
    ids = frame["participant_id"].to_numpy()
    demo = load_demographics(accession, list(ids))
    return frame, y, ids, demo


def _identity_auc(x_dev: np.ndarray, x_ext: np.ndarray, ids_dev, ids_ext, ext: str) -> float:
    x = np.vstack([x_dev, x_ext])
    y = np.array([1] * len(x_dev) + [0] * len(x_ext))
    groups = np.array([f"{DEV}:{i}" for i in ids_dev] + [f"{ext}:{i}" for i in ids_ext])
    cv = cross_validate_grouped(
        lambda: make_estimator("logreg", seed=SEED),
        x,
        y,
        groups,
        n_splits=5,
        n_repeats=5,
        seed=SEED,
    )
    return float(classification_metrics(cv.y_true, cv.y_pred, cv.y_score)["roc_auc"])


def run(log) -> dict:
    dev, y_dev, ids_dev, demo_dev = _load(DEV)
    cols = feature_columns(dev)
    out: dict = {
        "adr": "0014",
        "train_cohort": DEV,
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "cohorts": {},
    }
    for ext in EXTERNAL:
        frame, y_ext, ids_ext, demo_ext = _load(ext)
        if set(feature_columns(frame)) != set(cols):
            raise ValueError(f"feature columns differ for {ext}")
        entry: dict = {"n_test": len(y_ext), "n_test_pd": int(y_ext.sum()), "methods": {}}
        for method in METHODS:
            res: dict = {"models": {}}
            harmonized_all = None
            for label, model, family in MODELS:
                fcols = cols if family is None else family_columns(cols, family)
                x_tr, x_te = apply_harmonization(
                    dev[fcols].to_numpy(dtype=float),
                    frame[fcols].to_numpy(dtype=float),
                    method,
                    cov_train=demo_dev,
                    cov_test=demo_ext,
                )
                if family is None and harmonized_all is None:
                    harmonized_all = (x_tr, x_te)
                tr = evaluate_transfer(
                    lambda m=model: make_estimator(m, seed=SEED),
                    x_tr,
                    y_dev,
                    x_te,
                    y_ext,
                    ids_ext,
                    train_dataset=DEV,
                    test_dataset=ext,
                )
                cis = bootstrap_metric_cis(
                    tr.y_true, tr.y_pred, tr.y_score, n_boot=N_BOOT, seed=SEED
                )
                res["models"][label] = {
                    "roc_auc": cis["roc_auc"],
                    "balanced_accuracy": cis["balanced_accuracy"],
                }
            assert harmonized_all is not None
            res["dataset_identity_auc"] = _identity_auc(*harmonized_all, ids_dev, ids_ext, ext)
            entry["methods"][method] = res
            p = res["models"][PRIMARY]["roc_auc"]
            log.info(
                "%s %-18s logreg AUC %.3f [%.3f, %.3f] | identity AUC %.3f",
                ext,
                method,
                p["point"],
                p["lo"],
                p["hi"],
                res["dataset_identity_auc"],
            )
        out["cohorts"][ext] = entry

    # Pre-declared criterion: ComBat "helps" iff its all-feature logreg AUC beats
    # `none` in ALL external cohorts.
    out["criterion"] = {
        m: all(
            out["cohorts"][c]["methods"][m]["models"][PRIMARY]["roc_auc"]["point"]
            > out["cohorts"][c]["methods"]["none"]["models"][PRIMARY]["roc_auc"]["point"]
            for c in EXTERNAL
        )
        for m in ("combat", "combat_agesex")
    }
    return out


def _ci(m: dict) -> str:
    return f"{m['point']:.3f} [{m['lo']:.3f}, {m['hi']:.3f}]"


def render(p: dict) -> str:
    lines = [
        "# ComBat Harmonization (pre-declared, ADR 0014)",
        "",
        f"> Generated by `scripts/evaluate_combat.py` on {p['generated_utc']}. Each model "
        "is fit on the FULL ds007526 cohort and evaluated ONCE per external cohort after "
        "each harmonizer. Harmonizers see only unlabeled features (plus age/sex for "
        "`combat_agesex`), never test labels. Intervals are 95% participant-level "
        "bootstrap CIs. ComBat matches the reference `neuroCombat` implementation "
        "numerically (max abs diff ≤ 3e-7).",
        "",
        "## Primary comparison: all-feature logreg external ROC-AUC",
        "",
        "| cohort | n (PD) | none | per-cohort z-score | ComBat | ComBat (age/sex) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c, e in p["cohorts"].items():
        cells = [_ci(e["methods"][m]["models"][PRIMARY]["roc_auc"]) for m in METHODS]
        lines.append(f"| {c} | {e['n_test']} ({e['n_test_pd']}) | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Pre-declared criterion (ComBat AUC > `none` in all three cohorts): "
        + ", ".join(f"`{m}` **{'met' if ok else 'not met'}**" for m, ok in p["criterion"].items())
        + ".",
        "",
        "## Dataset identity after harmonization (ds007526 vs cohort; logreg AUC)",
        "",
        "| cohort | none | per-cohort z-score | ComBat | ComBat (age/sex) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c, e in p["cohorts"].items():
        cells = [f"{e['methods'][m]['dataset_identity_auc']:.3f}" for m in METHODS]
        lines.append(f"| {c} | " + " | ".join(cells) + " |")
    lines += ["", "## All models (external ROC-AUC)", ""]
    for c, e in p["cohorts"].items():
        lines += [
            f"### ds007526 -> {c}",
            "",
            "| model | none | per-cohort z-score | ComBat | ComBat (age/sex) |",
            "| --- | --- | --- | --- | --- |",
        ]
        for label, _, _ in MODELS:
            cells = [_ci(e["methods"][m]["models"][label]["roc_auc"]) for m in METHODS]
            lines.append(f"| {label} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += [
        "Research tool only: transductive harmonization uses each test cohort's own "
        "unlabeled feature distribution, so these results describe whether the "
        "cohorts can be compared, not a deployable model. Interpretation: ADR 0014.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    log = configure_logging()
    payload = run(log)
    TABLES_ROOT.mkdir(parents=True, exist_ok=True)
    (TABLES_ROOT / "combat.json").write_text(json.dumps(payload, indent=2))
    REPORT.write_text(render(payload))
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
