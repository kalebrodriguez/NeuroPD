"""Pre-registered within-PD clinical severity replication (ADR 0017).

In the PD participants of ds007526 and ds004584 (after QC), tests whether two
pre-specified EEG slowing markers relate to cognition (MoCA) in the predicted
direction at BOTH sites (age-partialled Spearman; Bonferroni alpha = 0.025).
Motor severity is secondary/descriptive; an all-feature MoCA scan is exploratory.

Writes ``reports/tables/clinical.json`` (git-ignored) and ``docs/clinical.md``.

Usage:
    uv run python scripts/evaluate_clinical.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from neuropd.data.audit import read_tsv, row_value
from neuropd.evaluation.clinical import (
    benjamini_hochberg,
    partial_spearman,
    partial_spearman_r,
)
from neuropd.features.matrix import feature_columns
from neuropd.logging import configure_logging

PROCESSED_ROOT = Path("data/processed")
RAW_ROOT = Path("data/raw")
TABLES_ROOT = Path("reports/tables")
REPORT = Path("docs/clinical.md")
ALPHA = 0.025
SEED, N_BOOT = 20240517, 2000
# cohort -> (MoCA column, motor column, motor label)
COHORTS = {
    "ds007526": ("moca", "updrs_part_iii", "MDS-UPDRS III"),
    "ds004584": ("MOCA", "UPDRS", "UPDRS (part undocumented)"),
}
REGIONS = ("frontal", "central", "temporal", "parietal", "occipital")
# marker -> predicted sign of the MoCA association
PRIMARY = {"occipital PAF": +1, "global theta/alpha ratio": -1}


def _num(v: str | None) -> float:
    try:
        return float(v) if v not in (None, "", "n/a") else float("nan")
    except ValueError:
        return float("nan")


def load(cohort: str) -> pd.DataFrame:
    """PD participants after QC with features, age, MoCA and motor score."""
    moca_col, motor_col, _ = COHORTS[cohort]
    feats = pd.read_parquet(PROCESSED_ROOT / f"features_{cohort}.parquet")
    feats = feats[feats["group"] == "PD"].copy()
    rows = {
        r["participant_id"].lstrip("﻿"): r for r in read_tsv(RAW_ROOT / cohort / "participants.tsv")
    }
    for name, col in (("age", "age"), ("moca", moca_col), ("motor", motor_col)):
        feats[name] = [_num(row_value(rows.get(p, {}), col)) for p in feats["participant_id"]]
    feats["occipital PAF"] = feats["paf__occipital__median"]
    feats["global theta/alpha ratio"] = feats[
        [f"theta_alpha_ratio__{r}__median" for r in REGIONS]
    ].mean(axis=1)
    return feats.reset_index(drop=True)


def _pc(frame: pd.DataFrame, feature: str, score: str) -> dict:
    res = partial_spearman(
        frame[feature].to_numpy(),
        frame[score].to_numpy(),
        frame[["age"]].to_numpy(),
        n_boot=N_BOOT,
        seed=SEED,
    )
    return {"r": res.r, "p": res.p, "n": res.n, "lo": res.lo, "hi": res.hi}


def run(log) -> dict:
    data = {c: load(c) for c in COHORTS}
    out: dict = {
        "adr": "0017",
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "alpha": ALPHA,
        "primary": {},
        "secondary_motor": {},
        "exploratory": {},
    }
    for marker, sign in PRIMARY.items():
        per = {c: _pc(d, marker, "moca") for c, d in data.items()}
        replicated = all(np.sign(v["r"]) == sign and v["p"] < ALPHA for v in per.values())
        out["primary"][marker] = {
            "predicted_sign": sign,
            "cohorts": per,
            "replicated": bool(replicated),
        }
        log.info(
            "%s vs MoCA: %s -> %s",
            marker,
            ", ".join(f"{c} r={v['r']:+.3f} p={v['p']:.4f} n={v['n']}" for c, v in per.items()),
            "REPLICATED" if replicated else "not replicated",
        )
        out["secondary_motor"][marker] = {c: _pc(d, marker, "motor") for c, d in data.items()}
    out["h3_supported"] = any(v["replicated"] for v in out["primary"].values())

    cols = [c for c in feature_columns(data["ds007526"]) if c.endswith("__median")]
    rs: dict[str, np.ndarray] = {}
    for c, d in data.items():
        r_vals, p_vals = [], []
        for f in cols:
            sub = d[[f, "moca", "age"]].dropna()
            r = partial_spearman_r(
                sub[f].to_numpy(), sub["moca"].to_numpy(), sub[["age"]].to_numpy()
            )
            dof = len(sub) - 3
            t = r * np.sqrt(dof / (1 - r**2))
            r_vals.append(r)
            p_vals.append(float(2 * stats.t.sf(abs(t), dof)))
        q = benjamini_hochberg(np.array(p_vals))
        rs[c] = np.array(r_vals)
        out["exploratory"][c] = {
            "n_features": len(cols),
            "n_fdr_significant": int(np.sum(q < 0.05)),
            "top": sorted(
                (
                    {"feature": f, "r": r, "q": float(qq)}
                    for f, r, qq in zip(cols, r_vals, q, strict=True)
                ),
                key=lambda e: e["q"],
            )[:5],
        }
    a, b = rs["ds007526"], rs["ds004584"]
    ok = np.isfinite(a) & np.isfinite(b)
    out["exploratory"]["cross_cohort"] = {
        "sign_agreement": float(np.mean(np.sign(a[ok]) == np.sign(b[ok]))),
        "spearman_of_coefficients": float(stats.spearmanr(a[ok], b[ok]).statistic),
        "n_features": int(ok.sum()),
    }
    return out


def _r(v: dict) -> str:
    return f"{v['r']:+.3f} [{v['lo']:+.2f}, {v['hi']:+.2f}], p={v['p']:.4f}, n={v['n']}"


def render(p: dict) -> str:
    L = [
        "# Within-PD Clinical Severity Replication (pre-registered, ADR 0017)",
        "",
        f"> Generated by `scripts/evaluate_clinical.py` on {p['generated_utc']}. PD "
        "participants after QC only. Spearman partial correlation controlling for age, "
        "two-sided t-test p, 95% bootstrap CI. Bonferroni alpha = 0.025 for the two "
        "primary markers.",
        "",
        "## Primary: EEG slowing vs cognition (MoCA)",
        "",
        "| marker (predicted sign) | ds007526 | ds004584 | replicated? |",
        "| --- | --- | --- | --- |",
    ]
    for m, v in p["primary"].items():
        sign = "+" if v["predicted_sign"] > 0 else "-"
        L.append(
            f"| {m} ({sign}) | {_r(v['cohorts']['ds007526'])} | {_r(v['cohorts']['ds004584'])} "
            f"| **{'yes' if v['replicated'] else 'no'}** |"
        )
    L += [
        "",
        f"**H3 {'supported' if p['h3_supported'] else 'not supported'}** "
        "(at least one marker must replicate: predicted sign and p < 0.025 at both sites).",
        "",
        "## Secondary (descriptive): motor severity",
        "",
        "ds007526 uses MDS-UPDRS part III; the ds004584 `UPDRS` column is documented only "
        'as "UPDRS score", so the two motor scales may differ.',
        "",
        "| marker | ds007526 | ds004584 |",
        "| --- | --- | --- |",
    ]
    for m, v in p["secondary_motor"].items():
        L.append(f"| {m} | {_r(v['ds007526'])} | {_r(v['ds004584'])} |")
    e = p["exploratory"]
    cc = e["cross_cohort"]
    L += [
        "",
        "## Exploratory: every median feature vs MoCA",
        "",
        f"Features passing BH-FDR q < 0.05: ds007526 {e['ds007526']['n_fdr_significant']}/"
        f"{e['ds007526']['n_features']}, ds004584 {e['ds004584']['n_fdr_significant']}/"
        f"{e['ds004584']['n_features']}. Cross-cohort sign agreement of the "
        f"{cc['n_features']} partial correlations: {cc['sign_agreement']:.0%} (50% = chance); "
        "Spearman correlation of the two coefficient vectors: "
        f"{cc['spearman_of_coefficients']:+.2f}.",
        "",
        "| cohort | strongest features (partial r, BH q) |",
        "| --- | --- |",
    ]
    for c in ("ds007526", "ds004584"):
        top = "; ".join(f"`{t['feature']}` {t['r']:+.2f} (q={t['q']:.3f})" for t in e[c]["top"])
        L.append(f"| {c} | {top} |")
    L += [
        "",
        "Association analyses on observational research data. Not diagnostic or "
        "prognostic. Interpretation: ADR 0017.",
        "",
    ]
    return "\n".join(L)


def main() -> int:
    log = configure_logging()
    payload = run(log)
    TABLES_ROOT.mkdir(parents=True, exist_ok=True)
    (TABLES_ROOT / "clinical.json").write_text(json.dumps(payload, indent=2))
    REPORT.write_text(render(payload))
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
