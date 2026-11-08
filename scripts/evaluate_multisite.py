"""Pre-declared leave-one-site-out multi-site training (ADR 0016).

For each held-out site, compares:
  A  single-site: fit on ds007526 only (reference; not for held-out ds007526)
  B  multi-site pooled: fit on the other three sites pooled
  C  multi-site per-site standardized: each site z-scored by its own unlabeled stats
Each model is fit once and evaluated once on the held-out site (bootstrap CIs).

Writes ``reports/tables/multisite.json`` (git-ignored) and ``docs/multisite.md``.

Usage:
    uv run python scripts/evaluate_multisite.py
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
from neuropd.evaluation.multisite import loso_folds, per_site_zscore, site_ids
from neuropd.features.families import PRIMARY_FAMILY, family_columns
from neuropd.features.matrix import feature_columns
from neuropd.logging import configure_logging
from neuropd.modeling.baselines import make_estimator
from neuropd.modeling.pipeline import cross_validate_grouped, positive_scores

PROCESSED_ROOT = Path("data/processed")
TABLES_ROOT = Path("reports/tables")
REPORT = Path("docs/multisite.md")
SITES = ("ds007526", "ds002778", "ds004584", "ds003490")
SINGLE = "ds007526"
ARMS = {
    "A": "single-site (ds007526)",
    "B": "multi-site pooled",
    "C": "multi-site per-site z",
}
MODELS = (
    ("logreg", "logreg", None),
    ("logreg (relative power)", "logreg", PRIMARY_FAMILY),
    ("svm_linear", "svm_linear", None),
    ("random_forest", "random_forest", None),
)
PRIMARY = "logreg"
SEED, N_BOOT = 20240517, 2000


def load_all() -> tuple[pd.DataFrame, list[str], np.ndarray]:
    frames = [pd.read_parquet(PROCESSED_ROOT / f"features_{s}.parquet") for s in SITES]
    cols = feature_columns(frames[0])
    for f in frames[1:]:
        if set(feature_columns(f)) != set(cols):
            raise ValueError("feature columns differ across sites")
    frame = pd.concat([f[["participant_id", "dataset", "group", *cols]] for f in frames])
    frame = frame.reset_index(drop=True)
    demo = np.vstack(
        [
            load_demographics(s, list(frame.loc[frame["dataset"] == s, "participant_id"]))
            for s in SITES
        ]
    )
    return frame, cols, demo


def _fit_eval(model: str, x_tr, y_tr, x_te, y_te) -> dict:
    est = make_estimator(model, seed=SEED).fit(x_tr, y_tr)
    score = positive_scores(est, x_te)
    pred = est.predict(x_te)
    cis = bootstrap_metric_cis(y_te, pred, score, n_boot=N_BOOT, seed=SEED)
    return {"roc_auc": cis["roc_auc"], "balanced_accuracy": cis["balanced_accuracy"]}


def _identity_auc(x: np.ndarray, sites: np.ndarray, uid: np.ndarray) -> float:
    """Multi-class-free summary: mean one-vs-rest site AUC among training sites."""
    aucs = []
    for s in np.unique(sites):
        y = (sites == s).astype(int)
        cv = cross_validate_grouped(
            lambda: make_estimator("logreg", seed=SEED),
            x,
            y,
            uid,
            n_splits=5,
            n_repeats=5,
            seed=SEED,
        )
        aucs.append(classification_metrics(cv.y_true, cv.y_pred, cv.y_score)["roc_auc"])
    return float(np.mean(aucs))


def run(log) -> dict:
    frame, cols, demo = load_all()
    sites = frame["dataset"].to_numpy()
    pids = frame["participant_id"].to_numpy()
    uid = site_ids(sites, pids)
    y = (frame["group"].to_numpy() == "PD").astype(int)
    x_raw = frame[cols].to_numpy(dtype=float)
    x_z = per_site_zscore(x_raw, sites)
    col_idx = {c: i for i, c in enumerate(cols)}
    out: dict = {
        "adr": "0016",
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "n_by_site": {s: int((sites == s).sum()) for s in SITES},
        "pd_fraction_by_site": {s: float(y[sites == s].mean()) for s in SITES},
        "folds": {},
    }
    single_idx = np.flatnonzero(sites == SINGLE)
    for fold in loso_folds(sites, pids):
        held = fold.held_out
        tr, te = fold.train_idx, fold.test_idx
        entry: dict = {
            "n_train": len(tr),
            "n_test": len(te),
            "n_test_pd": int(y[te].sum()),
            "train_sites": sorted(set(sites[tr].tolist())),
            "arms": {},
        }
        for arm in ARMS:
            if arm == "A" and held == SINGLE:
                continue
            train_rows = single_idx if arm == "A" else tr
            x = x_z if arm == "C" else x_raw
            res: dict = {}
            for label, model, family in MODELS:
                idx = [
                    col_idx[c] for c in (cols if family is None else family_columns(cols, family))
                ]
                res[label] = _fit_eval(
                    model, x[np.ix_(train_rows, idx)], y[train_rows], x[np.ix_(te, idx)], y[te]
                )
            if arm == "B":
                res["demographics"] = _fit_eval(
                    "demographics", demo[train_rows], y[train_rows], demo[te], y[te]
                )
            entry["arms"][arm] = res
        entry["training_site_identity_auc"] = {
            "B": _identity_auc(x_raw[tr], sites[tr], uid[tr]),
            "C": _identity_auc(x_z[tr], sites[tr], uid[tr]),
        }
        out["folds"][held] = entry
        msg = " | ".join(
            f"{a} {entry['arms'][a][PRIMARY]['roc_auc']['point']:.3f}" for a in entry["arms"]
        )
        log.info("held-out %s (n=%d): logreg AUC %s", held, len(te), msg)

    comparable = [s for s in SITES if s != SINGLE]

    def beats_a(arm: str) -> bool:
        return all(
            out["folds"][s]["arms"][arm][PRIMARY]["roc_auc"]["point"]
            > out["folds"][s]["arms"]["A"][PRIMARY]["roc_auc"]["point"]
            for s in comparable
        )

    out["criterion"] = {"B_beats_A_all": beats_a("B"), "C_beats_A_all": beats_a("C")}
    out["h2_supported"] = out["criterion"]["B_beats_A_all"] or out["criterion"]["C_beats_A_all"]
    return out


def _ci(m: dict) -> str:
    return f"{m['point']:.3f} [{m['lo']:.3f}, {m['hi']:.3f}]"


def render(p: dict) -> str:
    lines = [
        "# Leave-One-Site-Out Multi-Site Training (pre-declared, ADR 0016)",
        "",
        f"> Generated by `scripts/evaluate_multisite.py` on {p['generated_utc']}. Each "
        "held-out site is evaluated ONCE by models fit without it. Arm A trains on "
        "ds007526 only; arm B pools the other three sites; arm C z-scores every site by "
        "its own unlabeled statistics before pooling. Intervals are 95% participant-level "
        "bootstrap CIs.",
        "",
        "Sites (n, PD fraction): "
        + ", ".join(f"{s} ({p['n_by_site'][s]}, {p['pd_fraction_by_site'][s]:.0%})" for s in SITES)
        + ".",
        "",
        "## Primary: all-feature logreg external ROC-AUC",
        "",
        "| held-out site | n (PD) | A single-site | B multi-site pooled "
        "| C multi-site per-site z |",
        "| --- | --- | --- | --- | --- |",
    ]
    for s, f in p["folds"].items():
        cells = [_ci(f["arms"][a][PRIMARY]["roc_auc"]) if a in f["arms"] else "-" for a in ARMS]
        lines.append(f"| {s} | {f['n_test']} ({f['n_test_pd']}) | " + " | ".join(cells) + " |")
    c = p["criterion"]
    lines += [
        "",
        "Pre-declared H2 (B or C beats A in all three of ds002778, ds004584, ds003490): "
        f"B {'yes' if c['B_beats_A_all'] else 'no'}, C {'yes' if c['C_beats_A_all'] else 'no'} "
        f"→ **H2 {'supported' if p['h2_supported'] else 'not supported'}**.",
        "",
        "## All models (external ROC-AUC)",
        "",
    ]
    labels = [m[0] for m in MODELS]
    for s, f in p["folds"].items():
        lines += [
            f"### held out: {s} (trained on {', '.join(f['train_sites'])} for B/C)",
            "",
            "| model | " + " | ".join(ARMS[a] for a in f["arms"]) + " |",
            "| --- | " + " | ".join("---" for _ in f["arms"]) + " |",
        ]
        for label in labels:
            lines.append(
                f"| {label} | "
                + " | ".join(_ci(f["arms"][a][label]["roc_auc"]) for a in f["arms"])
                + " |"
            )
        if "demographics" in f["arms"].get("B", {}):
            lines.append(
                f"| demographics (age/sex, arm B) | "
                + " | ".join(
                    _ci(f["arms"]["B"]["demographics"]["roc_auc"]) if a == "B" else "-"
                    for a in f["arms"]
                )
                + " |"
            )
        ti = f["training_site_identity_auc"]
        lines += [
            "",
            f"Site identity among the training sites (mean one-vs-rest AUC): raw {ti['B']:.3f}, "
            f"per-site z {ti['C']:.3f}.",
            "",
        ]
    lines += [
        "Research tool only: group-level estimates, not a diagnostic test. "
        "Interpretation: ADR 0016.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    log = configure_logging()
    payload = run(log)
    TABLES_ROOT.mkdir(parents=True, exist_ok=True)
    (TABLES_ROOT / "multisite.json").write_text(json.dumps(payload, indent=2))
    REPORT.write_text(render(payload))
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
