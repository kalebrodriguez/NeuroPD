"""Sensitivity of the main results to the QC rejection threshold (pre-declared, ADR 0020).

For each arm (150 µV primary, 200 µV, 400 µV), with features produced by
``scripts/preprocess.py --reject-uv`` / ``scripts/extract_features.py --processed-root``:

1. ADR 0013 transfer: relative-power logreg trained on ds007526, evaluated once on
   ds004584 and ds003490 (ROC-AUC, participant bootstrap CI; confirmed iff lo > 0.5).
2. Site identity (ds007526 vs cohort, grouped CV) vs all-feature logreg transfer, for
   ds002778, ds004584 and ds003490.
3. ADR 0017: within-PD global theta/alpha ratio vs MoCA (age-partialled Spearman) at
   ds007526 and ds004584 (replicates iff negative and p < 0.025 at both).

The 150 µV arm recomputes the committed results and must reproduce them, which
checks the procedure. Writes ``reports/tables/qc_threshold.json`` (git-ignored) and
``docs/qc_threshold.md``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

import evaluate_clinical as clin
from evaluate_combat import _identity_auc
from neuropd.evaluation.bootstrap import bootstrap_metric_cis
from neuropd.evaluation.transfer import evaluate_transfer
from neuropd.features.families import PRIMARY_FAMILY, family_columns
from neuropd.features.matrix import feature_columns
from neuropd.modeling.baselines import make_estimator

ARMS = {
    "150": Path("data/processed"),
    "200": Path("data/processed_qc200"),
    "400": Path("data/processed_qc400"),
}
PRIMARY_ARM = "150"
DEV = "ds007526"
EXTERNAL = ("ds002778", "ds004584", "ds003490")
CONFIRMATORY = ("ds004584", "ds003490")
CLINICAL = ("ds007526", "ds004584")
MARKER = "global theta/alpha ratio"
H1_THRESHOLD, ALPHA = 0.5, 0.025
SEED, N_BOOT = 20240517, 2000
TABLES_ROOT = Path("reports/tables")
REPORT = Path("docs/qc_threshold.md")


def _features(root: Path, cohort: str) -> pd.DataFrame:
    return pd.read_parquet(root / f"features_{cohort}.parquet")


def _transfer(dev: pd.DataFrame, ext: pd.DataFrame, cols: list[str], name: str) -> dict:
    y_dev = (dev["group"].to_numpy() == "PD").astype(int)
    y_ext = (ext["group"].to_numpy() == "PD").astype(int)
    tr = evaluate_transfer(
        lambda: make_estimator("logreg", seed=SEED),
        dev[cols].to_numpy(dtype=float),
        y_dev,
        ext[cols].to_numpy(dtype=float),
        y_ext,
        ext["participant_id"].to_numpy(),
        train_dataset=DEV,
        test_dataset=name,
    )
    return bootstrap_metric_cis(tr.y_true, tr.y_pred, tr.y_score, n_boot=N_BOOT, seed=SEED)[
        "roc_auc"
    ]


def evaluate_arm(root: Path) -> dict:
    frames = {c: _features(root, c) for c in (DEV, *EXTERNAL)}
    cols = feature_columns(frames[DEV])
    rel = family_columns(cols, PRIMARY_FAMILY)
    dev = frames[DEV]
    out: dict = {
        "n": {
            c: {str(k): int(v) for k, v in f["group"].value_counts().sort_index().items()}
            for c, f in frames.items()
        },
        "participants": {c: sorted(f["participant_id"]) for c, f in frames.items()},
        "transfer_all": {},
        "transfer_relative_power": {},
        "identity": {},
    }
    for c in EXTERNAL:
        ext = frames[c]
        if set(feature_columns(ext)) != set(cols):
            raise ValueError(f"feature columns differ for {c}")
        out["transfer_all"][c] = _transfer(dev, ext, cols, c)
        out["identity"][c] = _identity_auc(
            dev[cols].to_numpy(dtype=float),
            ext[cols].to_numpy(dtype=float),
            dev["participant_id"].to_numpy(),
            ext["participant_id"].to_numpy(),
            c,
        )
        if c in CONFIRMATORY:
            out["transfer_relative_power"][c] = _transfer(dev, ext, rel, c)
    clin.PROCESSED_ROOT = root
    out["clinical"] = {c: clin._pc(clin.load(c), MARKER, "moca") for c in CLINICAL}
    return out


def verdicts(arm: dict) -> dict:
    """The three pre-declared verdicts for one arm (pure function)."""
    return {
        "h1_ds004584_confirmed": arm["transfer_relative_power"]["ds004584"]["lo"] > H1_THRESHOLD,
        "h1_ds003490_confirmed": arm["transfer_relative_power"]["ds003490"]["lo"] > H1_THRESHOLD,
        "identity_exceeds_transfer": all(
            arm["identity"][c] > arm["transfer_all"][c]["point"] for c in EXTERNAL
        ),
        "adr0017_replicates": all(v["r"] < 0 and v["p"] < ALPHA for v in arm["clinical"].values()),
    }


def apply_rule(arms: dict) -> dict:
    """ADR 0020 rule: every lenient arm reproduces the expected verdicts."""
    expected = {
        "h1_ds004584_confirmed": True,
        "h1_ds003490_confirmed": False,
        "identity_exceeds_transfer": True,
        "adr0017_replicates": True,
    }
    per_arm = {a: verdicts(v) for a, v in arms.items()}
    rule = {
        a: {
            "a_h1_verdicts_unchanged": v["h1_ds004584_confirmed"]
            == expected["h1_ds004584_confirmed"]
            and v["h1_ds003490_confirmed"] == expected["h1_ds003490_confirmed"],
            "b_identity_exceeds_transfer": v["identity_exceeds_transfer"],
            "c_adr0017_unchanged": v["adr0017_replicates"],
        }
        for a, v in per_arm.items()
        if a != PRIMARY_ARM
    }
    return {
        "verdicts": per_arm,
        "rule": rule,
        "robust": all(all(r.values()) for r in rule.values()),
    }


def run(log) -> dict:
    arms = {}
    for name, root in ARMS.items():
        log.info("ADR 0020: evaluating %s µV arm from %s", name, root)
        arms[name] = evaluate_arm(root)
    primary_ids = {c: set(v) for c, v in arms[PRIMARY_ARM]["participants"].items()}
    for arm in arms.values():
        ids = {c: set(v) for c, v in arm.pop("participants").items()}  # ids never stored
        arm["added_by_cohort"] = {c: len(ids[c] - primary_ids[c]) for c in ids}
        arm["dropped_by_cohort"] = {c: len(primary_ids[c] - ids[c]) for c in ids}
        arm["n_added_vs_primary"] = sum(arm["added_by_cohort"].values())
        arm["n_dropped_vs_primary"] = sum(arm["dropped_by_cohort"].values())
    out = {
        "adr": "0020",
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "arms": arms,
        **apply_rule(arms),
    }
    log.info("ADR 0020 rule: %s -> robust=%s", out["rule"], out["robust"])
    return out


def _ci(m: dict) -> str:
    return f"{m['point']:.3f} [{m['lo']:.3f}, {m['hi']:.3f}]"


def _yes(b: bool) -> str:
    return "yes" if b else "**no**"


def render(p: dict) -> str:
    arms = p["arms"]
    names = list(arms)
    head = "| | " + " | ".join(
        f"{a} µV" + (" (primary)" if a == PRIMARY_ARM else "") for a in names
    )
    sep = "| --- |" + " --- |" * len(names)
    lines = [
        "# Sensitivity to the Quality-Control Threshold (pre-declared, ADR 0020)",
        "",
        f"> Generated by `scripts/evaluate_qc_threshold.py` on {p['generated_utc']}. All "
        "four cohorts were re-preprocessed with only the epoch rejection threshold "
        "changed (150 µV primary; 200 and 400 µV lenient); every other step is the "
        "conservative pipeline. Intervals are 95% participant-level bootstrap CIs.",
        "",
        "## Pre-declared rule",
        "",
        "| check | " + " | ".join(f"{a} µV" for a in p["rule"]) + " |",
        "| --- |" + " --- |" * len(p["rule"]),
    ]
    labels = {
        "a_h1_verdicts_unchanged": "(a) ADR 0013 verdicts unchanged",
        "b_identity_exceeds_transfer": "(b) site identity > disease transfer, all 3 cohorts",
        "c_adr0017_unchanged": "(c) ADR 0017 theta/alpha-MoCA still replicates",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | " + " | ".join(_yes(r[key]) for r in p["rule"].values()) + " |")
    lines += [
        "",
        "Verdict: the main results are **"
        + ("robust" if p["robust"] else "not robust (see rows marked no)")
        + "** to the QC threshold.",
        "",
        "## Participants retained (PD / control)",
        "",
        head + " |",
        sep,
    ]
    for c in arms[PRIMARY_ARM]["n"]:
        cells = [f"{a['n'][c].get('PD', 0)} / {a['n'][c].get('HC', 0)}" for a in arms.values()]
        lines.append(f"| {c} | " + " | ".join(cells) + " |")
    lines.append(
        "| added vs primary | "
        + " | ".join(str(a["n_added_vs_primary"]) for a in arms.values())
        + " |"
    )
    lines += [
        "",
        "## ADR 0013: relative-power transfer from ds007526 (ROC-AUC)",
        "",
        head + " |",
        sep,
    ]
    for c in CONFIRMATORY:
        lines.append(
            f"| {c} | "
            + " | ".join(_ci(a["transfer_relative_power"][c]) for a in arms.values())
            + " |"
        )
    lines += [
        "",
        "## Site identity vs all-feature disease transfer (ROC-AUC)",
        "",
        head + " |",
        sep,
    ]
    for c in EXTERNAL:
        lines.append(
            f"| {c} | "
            + " | ".join(
                f"{a['identity'][c]:.3f} vs {a['transfer_all'][c]['point']:.3f}"
                for a in arms.values()
            )
            + " |"
        )
    lines += [
        "",
        "## ADR 0017: within-PD global theta/alpha ratio vs MoCA (age-partialled r)",
        "",
        head + " |",
        sep,
    ]
    for c in CLINICAL:
        lines.append(
            f"| {c} | "
            + " | ".join(
                f"{a['clinical'][c]['r']:+.3f} (p={a['clinical'][c]['p']:.3f}, "
                f"n={a['clinical'][c]['n']})"
                for a in arms.values()
            )
            + " |"
        )
    lines += [
        "",
        "Research tool only: group-level estimates, not a diagnostic test. "
        "Interpretation: ADR 0020.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    from neuropd.logging import configure_logging

    log = configure_logging()
    payload = run(log)
    TABLES_ROOT.mkdir(parents=True, exist_ok=True)
    (TABLES_ROOT / "qc_threshold.json").write_text(json.dumps(payload, indent=2))
    REPORT.write_text(render(payload))
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
