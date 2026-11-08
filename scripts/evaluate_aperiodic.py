"""Pre-declared spectral-parameterization aperiodic analysis (ADR 0015).

Compares the peak-separated (fooof/specparam) aperiodic fit against the ADR 0012
log-log fit, both computed on the same epoch-averaged spectra:

* fit quality (specparam R^2) per cohort;
* PD - control effect size (Cohen's d, bootstrap CI) of the region-mean exponent;
* transfer of aperiodic-only logreg (ds007526 -> each external cohort);
* swap-in: all-feature logreg with the ADR 0012 aperiodic columns replaced.

Writes ``reports/tables/aperiodic_specparam.json`` and ``docs/aperiodic_specparam.md``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from neuropd.evaluation.bootstrap import bootstrap_metric_cis
from neuropd.evaluation.transfer import evaluate_transfer
from neuropd.features.matrix import feature_columns
from neuropd.logging import configure_logging
from neuropd.modeling.baselines import make_estimator

PROCESSED_ROOT = Path("data/processed")
TABLES_ROOT = Path("reports/tables")
REPORT = Path("docs/aperiodic_specparam.md")
DEV = "ds007526"
EXTERNAL = ("ds002778", "ds004584", "ds003490")
COHORTS = (DEV, *EXTERNAL)
METHODS = {"log-log (ADR 0012)": "ll", "spectral parameterization": "sp"}
SEED, N_BOOT = 20240517, 2000


def _ap(accession: str) -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_ROOT / f"aperiodic_{accession}.parquet")


def _cols(frame: pd.DataFrame, prefix: str) -> list[str]:
    return [c for c in frame.columns if c.startswith(f"{prefix}_exponent__")] + [
        c for c in frame.columns if c.startswith(f"{prefix}_offset__")
    ]


def cohens_d_ci(pd_vals: np.ndarray, hc_vals: np.ndarray, rng: np.random.Generator) -> dict:
    """PD - control Cohen's d (pooled SD) with a 95% bootstrap CI (resampling within group)."""

    def d(a: np.ndarray, b: np.ndarray) -> float:
        pooled = np.sqrt(
            ((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2)
        )
        return float((a.mean() - b.mean()) / pooled) if pooled > 0 else float("nan")

    boots = [
        d(rng.choice(pd_vals, len(pd_vals)), rng.choice(hc_vals, len(hc_vals)))
        for _ in range(N_BOOT)
    ]
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    return {"point": d(pd_vals, hc_vals), "lo": float(lo), "hi": float(hi)}


def _transfer(x_tr, y_tr, x_te, y_te, ids, ext) -> dict:
    res = evaluate_transfer(
        lambda: make_estimator("logreg", seed=SEED),
        x_tr,
        y_tr,
        x_te,
        y_te,
        ids,
        train_dataset=DEV,
        test_dataset=ext,
    )
    return bootstrap_metric_cis(res.y_true, res.y_pred, res.y_score, n_boot=N_BOOT, seed=SEED)[
        "roc_auc"
    ]


def run(log) -> dict:
    rng = np.random.default_rng(SEED)
    out: dict = {"adr": "0015", "generated_utc": datetime.now(UTC).isoformat(timespec="seconds")}

    # 2. fit quality + 3. group effect on the region-mean exponent
    quality, effect = {}, {}
    for c in COHORTS:
        f = _ap(c)
        r2 = f.filter(like="sp_r2__").to_numpy().ravel()
        quality[c] = {"median": float(np.median(r2)), "min": float(r2.min()), "n": len(f)}
        is_pd = f["group"].to_numpy() == "PD"
        effect[c] = {}
        for label, pre in METHODS.items():
            mean_exp = f.filter(like=f"{pre}_exponent__").mean(axis=1).to_numpy()
            effect[c][label] = cohens_d_ci(mean_exp[is_pd], mean_exp[~is_pd], rng)
        log.info(
            "%s r2 median %.3f | d(ll) %.2f d(sp) %.2f",
            c,
            quality[c]["median"],
            effect[c]["log-log (ADR 0012)"]["point"],
            effect[c]["spectral parameterization"]["point"],
        )
    out["fit_quality"], out["group_effect"] = quality, effect

    # 4. aperiodic-only transfer and 5. swap-in
    dev_ap = _ap(DEV)
    dev_feat = pd.read_parquet(PROCESSED_ROOT / f"features_{DEV}.parquet")
    fcols = feature_columns(dev_feat)
    keep = [c for c in fcols if not c.startswith("aperiodic_")]
    dev_all = dev_feat.merge(dev_ap[["participant_id", *_cols(dev_ap, "sp")]], on="participant_id")
    y_dev = (dev_ap["group"].to_numpy() == "PD").astype(int)
    transfer, swap = {}, {}
    for ext in EXTERNAL:
        ap = _ap(ext)
        y = (ap["group"].to_numpy() == "PD").astype(int)
        ids = ap["participant_id"].to_numpy()
        transfer[ext] = {}
        for label, pre in METHODS.items():
            cols = _cols(dev_ap, pre)
            transfer[ext][label] = _transfer(
                dev_ap[cols].to_numpy(float), y_dev, ap[cols].to_numpy(float), y, ids, ext
            )
        feat = pd.read_parquet(PROCESSED_ROOT / f"features_{ext}.parquet")
        ext_all = feat.merge(ap[["participant_id", *_cols(ap, "sp")]], on="participant_id")
        y_all = (ext_all["group"].to_numpy() == "PD").astype(int)
        y_dev_all = (dev_all["group"].to_numpy() == "PD").astype(int)
        swapped = keep + _cols(dev_ap, "sp")
        swap[ext] = {
            "230 features (log-log aperiodic)": _transfer(
                dev_all[fcols].to_numpy(float),
                y_dev_all,
                ext_all[fcols].to_numpy(float),
                y_all,
                ext_all["participant_id"].to_numpy(),
                ext,
            ),
            "aperiodic swapped to spectral parameterization": _transfer(
                dev_all[swapped].to_numpy(float),
                y_dev_all,
                ext_all[swapped].to_numpy(float),
                y_all,
                ext_all["participant_id"].to_numpy(),
                ext,
            ),
        }
        log.info(
            "%s aperiodic-only AUC ll %.3f sp %.3f | swap %.3f -> %.3f",
            ext,
            transfer[ext]["log-log (ADR 0012)"]["point"],
            transfer[ext]["spectral parameterization"]["point"],
            *[v["point"] for v in swap[ext].values()],
        )
    out["aperiodic_only_transfer"], out["swap_in"] = transfer, swap
    out["criterion_sp_helps_transfer"] = all(
        transfer[e]["spectral parameterization"]["point"]
        > transfer[e]["log-log (ADR 0012)"]["point"]
        for e in EXTERNAL
    )
    return out


def _ci(m: dict, nd: int = 3) -> str:
    return f"{m['point']:.{nd}f} [{m['lo']:.{nd}f}, {m['hi']:.{nd}f}]"


def render(p: dict) -> str:
    L = [
        "# Peak-Separated Aperiodic Fit (pre-declared, ADR 0015)",
        "",
        f"> Generated by `scripts/evaluate_aperiodic.py` on {p['generated_utc']}. Spectral "
        "parameterization (`fooof` 1.1.1; the stable release of `specparam`) and the ADR "
        "0012 log-log fit are computed on the same epoch-averaged spectra (2-40 Hz) per "
        "participant and channel, then averaged within regions. Intervals are 95% "
        "bootstrap CIs.",
        "",
        "## Fit quality (spectral parameterization R², region means)",
        "",
        "| cohort | n | median R² | min R² |",
        "| --- | --- | --- | --- |",
    ]
    for c, q in p["fit_quality"].items():
        L.append(f"| {c} | {q['n']} | {q['median']:.3f} | {q['min']:.3f} |")
    L += [
        "",
        "## PD - control difference in aperiodic exponent (Cohen's d, region mean)",
        "",
        "| cohort | log-log (ADR 0012) | spectral parameterization |",
        "| --- | --- | --- |",
    ]
    for c, e in p["group_effect"].items():
        L.append(f"| {c} | " + " | ".join(_ci(e[m], 2) for m in METHODS) + " |")
    L += [
        "",
        "## Transfer: logreg on aperiodic features only (10 features), trained on ds007526",
        "",
        "| cohort | log-log (ADR 0012) | spectral parameterization |",
        "| --- | --- | --- |",
    ]
    for c, t in p["aperiodic_only_transfer"].items():
        L.append(f"| {c} | " + " | ".join(_ci(t[m]) for m in METHODS) + " |")
    L += [
        "",
        "Pre-declared criterion (spectral parameterization AUC higher in all three cohorts): "
        f"**{'met' if p['criterion_sp_helps_transfer'] else 'not met'}**.",
        "",
        "## Swap-in: all-feature logreg external AUC",
        "",
        "| cohort | 230 features (log-log aperiodic) "
        "| aperiodic swapped to spectral parameterization |",
        "| --- | --- | --- |",
    ]
    for c, s in p["swap_in"].items():
        L.append(f"| {c} | " + " | ".join(_ci(v) for v in s.values()) + " |")
    L += [
        "",
        "Research tool only: group-level estimates, not a diagnostic test. "
        "Interpretation: ADR 0015.",
        "",
    ]
    return "\n".join(L)


def main() -> int:
    log = configure_logging()
    payload = run(log)
    TABLES_ROOT.mkdir(parents=True, exist_ok=True)
    (TABLES_ROOT / "aperiodic_specparam.json").write_text(json.dumps(payload, indent=2))
    REPORT.write_text(render(payload))
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
