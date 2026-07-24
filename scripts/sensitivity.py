"""Sensitivity analyses (spec Section 14.5).

Tests whether the main findings survive reasonable alternative choices. Three
pre-declared analyses on the development cohort (internal, participant-grouped CV)
and, where relevant, the frozen external transfer:

1. **Harmonization** — region-level vs. exact shared-channel features (Section 11).
2. **Age/sex adjustment** — does EEG add signal *beyond* demographics? Compares
   demographics-only, EEG, EEG with age/sex linearly partialled out (fitted inside
   each training fold, no leakage), and EEG + demographics.
3. **Feature family** — which feature groups (relative / absolute / log power,
   slowing, complexity) carry and transfer signal.

Writes committed ``docs/sensitivity.md`` and ``reports/tables/sensitivity.json``.

Usage:
    uv run python scripts/sensitivity.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import StratifiedGroupKFold

from neuropd.data.demographics import load_demographics
from neuropd.data.splits import assert_participants_disjoint
from neuropd.evaluation.metrics import classification_metrics
from neuropd.evaluation.transfer import evaluate_transfer
from neuropd.features.matrix import feature_columns
from neuropd.logging import configure_logging
from neuropd.modeling.baselines import make_estimator
from neuropd.modeling.pipeline import cross_validate_grouped, positive_scores

PROCESSED_ROOT = Path("data/processed")
TABLES_ROOT = Path("reports/tables")
REPORT = Path("docs/sensitivity.md")
DEV, EXT = "ds007526", "ds002778"
SEED, N_SPLITS, N_REPEATS = 20240517, 5, 5

FAMILIES = {
    "relative power": lambda c: c.startswith("rel_power_"),
    "absolute power": lambda c: c.startswith("abs_power_"),
    "log power": lambda c: c.startswith("log_power_"),
    "slowing (paf/sef/ratios)": lambda c: (
        c.split("__")[0] in {"paf", "sef", "theta_alpha_ratio", "delta_alpha_ratio"}
    ),
    "complexity": lambda c: (
        c.split("__")[0]
        in {
            "spectral_entropy",
            "perm_entropy",
            "hjorth_activity",
            "hjorth_mobility",
            "hjorth_complexity",
        }
    ),
}


def _load(accession: str, suffix: str = ""):
    frame = pd.read_parquet(PROCESSED_ROOT / f"features_{accession}{suffix}.parquet")
    y = (frame["group"].to_numpy() == "PD").astype(int)
    ids = frame["participant_id"].to_numpy()
    return frame, y, ids, feature_columns(frame)


def _internal(x, y, groups, model="logreg") -> dict[str, float]:
    cv = cross_validate_grouped(
        lambda: make_estimator(model, seed=SEED),
        x,
        y,
        groups,
        n_splits=N_SPLITS,
        n_repeats=N_REPEATS,
        seed=SEED,
    )
    return classification_metrics(cv.y_true, cv.y_pred, cv.y_score)


def _external(x_tr, y_tr, x_te, y_te, ids_te, model="logreg") -> dict[str, float]:
    res = evaluate_transfer(
        lambda: make_estimator(model, seed=SEED),
        x_tr,
        y_tr,
        x_te,
        y_te,
        ids_te,
        train_dataset=DEV,
        test_dataset=EXT,
    )
    return classification_metrics(res.y_true, res.y_pred, res.y_score)


def _residualized_internal(x_eeg, demo, y, groups) -> dict[str, float]:
    """Internal CV where age/sex are linearly partialled out of EEG features in-fold."""
    n = len(y)
    score_sum = np.zeros(n)
    pred_sum = np.zeros(n)
    counts = np.zeros(n)
    for rep in range(N_REPEATS):
        cv = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED + rep)
        for tr, te in cv.split(x_eeg, y, groups):
            assert_participants_disjoint(
                {"train": groups[tr].tolist(), "test": groups[te].tolist()}
            )
            imp = SimpleImputer(strategy="median").fit(demo[tr])
            d_tr, d_te = imp.transform(demo[tr]), imp.transform(demo[te])
            reg = LinearRegression().fit(d_tr, x_eeg[tr])  # predict each EEG feature from age/sex
            res_tr = x_eeg[tr] - reg.predict(d_tr)
            res_te = x_eeg[te] - reg.predict(d_te)
            est = make_estimator("logreg", seed=SEED).fit(res_tr, y[tr])
            score_sum[te] += positive_scores(est, res_te)
            pred_sum[te] += est.predict(res_te)
            counts[te] += 1
    return classification_metrics(y, (pred_sum / counts >= 0.5).astype(int), score_sum / counts)


def _fmt(m: dict[str, float]) -> str:
    return f"{m['balanced_accuracy']:.3f} / {m['roc_auc']:.3f}"


def run() -> dict:
    log = configure_logging()
    reg_frame, y, ids, reg_cols = _load(DEV)
    x_region = reg_frame[reg_cols].to_numpy(dtype=float)
    ext_frame, y_ext, ids_ext, _ = _load(EXT)
    x_region_ext = ext_frame[reg_cols].to_numpy(dtype=float)
    demo = load_demographics(DEV, list(ids))

    out: dict = {
        "development": DEV,
        "external": EXT,
        "note": "values are balanced_accuracy / ROC-AUC",
    }

    # 1. Harmonization: region vs channel ------------------------------------
    harm = {
        "region": {
            "internal": _internal(x_region, y, ids),
            "external": _external(x_region, y, x_region_ext, y_ext, ids_ext),
        }
    }
    ch_path = PROCESSED_ROOT / f"features_{DEV}_channel.parquet"
    if ch_path.is_file():
        ch_frame, _, ch_ids, ch_cols = _load(DEV, "_channel")
        ch_ext_frame, _, ch_ids_ext, _ = _load(EXT, "_channel")
        x_ch = ch_frame[ch_cols].to_numpy(dtype=float)
        x_ch_ext = ch_ext_frame[ch_cols].to_numpy(dtype=float)
        harm["channel"] = {
            "internal": _internal(x_ch, y, ch_ids),
            "external": _external(x_ch, y, x_ch_ext, y_ext, ch_ids_ext),
            "n_features": len(ch_cols),
        }
    else:
        log.warning(
            "channel features not found (%s); run extract_features --spatial channel", ch_path
        )
    harm["region"]["n_features"] = len(reg_cols)
    out["harmonization"] = harm
    for k, v in harm.items():
        log.info(
            "harmonization %-8s internal %s | external %s",
            k,
            _fmt(v["internal"]),
            _fmt(v["external"]),
        )

    # 2. Age/sex adjustment --------------------------------------------------
    adj = {
        "demographics_only": _internal(demo, y, ids),
        "eeg": harm["region"]["internal"],
        "eeg_residualized_on_agesex": _residualized_internal(x_region, demo, y, ids),
        "eeg_plus_demographics": _internal(np.hstack([x_region, demo]), y, ids),
    }
    out["age_sex_adjustment"] = adj
    for k, v in adj.items():
        log.info("age/sex %-28s internal %s", k, _fmt(v))

    # 3. Feature family ------------------------------------------------------
    fam = {}
    for name, pred in FAMILIES.items():
        cols = [c for c in reg_cols if pred(c)]
        if not cols:
            continue
        xf = reg_frame[cols].to_numpy(dtype=float)
        xf_ext = ext_frame[cols].to_numpy(dtype=float)
        fam[name] = {
            "n_features": len(cols),
            "internal": _internal(xf, y, ids),
            "external": _external(xf, y, xf_ext, y_ext, ids_ext),
        }
        log.info(
            "family %-26s (%3d) internal %s | external %s",
            name,
            len(cols),
            _fmt(fam[name]["internal"]),
            _fmt(fam[name]["external"]),
        )
    out["feature_family"] = fam
    return out


def _md(payload: dict) -> str:
    def row(label, m):
        return f"| {label} | {m['balanced_accuracy']:.3f} | {m['roc_auc']:.3f} |"

    lines = [
        "# Sensitivity Analyses",
        "",
        "> Generated by `scripts/sensitivity.py`. Development cohort ds007526, "
        "participant-grouped 5x5 CV (internal) and the frozen external transfer to "
        "ds002778. Do the main findings survive alternative choices? (spec Section 14.5)",
        "",
        "## 1. Channel harmonization: region vs. shared-channel features",
        "",
        "| features | internal bal acc | internal AUC | external bal acc | external AUC |",
        "| --- | --- | --- | --- | --- |",
    ]
    for k, v in payload["harmonization"].items():
        i, e = v["internal"], v["external"]
        lines.append(
            f"| {k} ({v.get('n_features', '?')}) | {i['balanced_accuracy']:.3f} | "
            f"{i['roc_auc']:.3f} | {e['balanced_accuracy']:.3f} | {e['roc_auc']:.3f} |"
        )
    lines += [
        "",
        "## 2. Age/sex adjustment (internal) — does EEG add signal beyond demographics?",
        "",
        "Age/sex are linearly partialled out of the EEG features **inside each training "
        "fold** (no leakage). If residualized EEG stays above chance, EEG carries signal "
        "independent of demographics.",
        "",
        "| model | balanced acc | ROC-AUC |",
        "| --- | --- | --- |",
    ]
    for k, v in payload["age_sex_adjustment"].items():
        lines.append(row(k.replace("_", " "), v))
    lines += [
        "",
        "## 3. Feature family (which groups carry / transfer signal)",
        "",
        "| family | n | internal bal acc | internal AUC | external bal acc | external AUC |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, v in payload["feature_family"].items():
        i, e = v["internal"], v["external"]
        lines.append(
            f"| {name} | {v['n_features']} | {i['balanced_accuracy']:.3f} | {i['roc_auc']:.3f} "
            f"| {e['balanced_accuracy']:.3f} | {e['roc_auc']:.3f} |"
        )
    lines += [
        "",
        "Interpretation is added to `docs/decisions/0010-sensitivity-analyses.md`. These "
        "are pre-declared robustness checks, not a search for the best result (Section 3.3).",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    payload = run()
    TABLES_ROOT.mkdir(parents=True, exist_ok=True)
    (TABLES_ROOT / "sensitivity.json").write_text(json.dumps(payload, indent=2))
    REPORT.write_text(_md(payload))
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
