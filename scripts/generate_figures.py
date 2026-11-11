"""Generate the manuscript figures (``docs/figures/*.svg``) from committed results.

Every value is read from the de-identified bundles in ``dashboard/data/``. The SVGs
are written deterministically (fixed hash salt, no timestamp, text as paths), so
``tests/test_manuscript.py`` can fail if a committed figure is stale.

Figure 1: cross-site disease transfer (ROC-AUC, 95% CI) for a model trained on
ds007526, all features vs the pre-registered relative-power family, with the
site-identity AUC for the same cohort pair.
Figure 2: within-PD theta/alpha-MoCA partial correlation under the ADR 0017
reference and the pre-declared ADR 0018 checks, per cohort, plus the pooled
estimate.

Usage:
    uv run python scripts/generate_figures.py            # write the figures
    uv run python scripts/generate_figures.py --check    # exit 1 if stale
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path("dashboard/data")
OUT = Path("docs/figures")
EXTERNAL = ("ds002778", "ds004584", "ds003490")

# Reference palette (dataviz skill, light mode): categorical slots 1-2 and text inks.
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d4"
P_COL = 0.12  # x position (partial r units) of the p-value column in figure 2

plt.rcParams.update(
    {
        "svg.hashsalt": "neuropd",
        "svg.fonttype": "path",
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": INK2,
        "axes.labelcolor": INK,
        "xtick.color": INK2,
        "ytick.color": INK,
        "text.color": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text())


def _errbar(ax, y, m: dict, color: str, marker: str, label: str | None, key: str) -> None:
    ax.errorbar(
        m[key],
        y,
        xerr=[[m[key] - m["lo"]], [m["hi"] - m[key]]],
        fmt=marker,
        color=color,
        ecolor=color,
        elinewidth=2,
        capsize=0,
        markersize=7,
        markeredgecolor="white",
        markeredgewidth=1,
        label=label,
    )


def fig_transfer() -> plt.Figure:
    combat = _load("combat.json")
    metrics = _load("metrics.json")
    conf = {c: _load(f"confirmatory_{c}.json") for c in ("ds004584", "ds003490")}
    ident = {
        "ds002778": metrics["dataset_shift"]["results"]["logreg"]["roc_auc"],
        "ds004584": conf["ds004584"]["dataset_identity"]["logreg"]["roc_auc"],
        "ds003490": conf["ds003490"]["dataset_identity"]["logreg"]["roc_auc"],
    }
    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1, 2.2]}, sharey=True
    )
    ys = list(range(len(EXTERNAL)))[::-1]
    labels = []
    for y, c in zip(ys, EXTERNAL, strict=True):
        e = combat["cohorts"][c]
        labels.append(f"{c}\nn={e['n_test']} ({e['n_test_pd']} PD)")
        ax_a.plot(ident[c], y, "o", color=INK2, markersize=7, markeredgecolor="white")
        allf = e["methods"]["none"]["models"]["logreg"]["roc_auc"]
        _errbar(ax_b, y + 0.13, allf, BLUE, "o", "all features" if y == ys[0] else None, "point")
        if c in conf:
            rel = conf[c]["primary"]["external"]["roc_auc"]
            _errbar(
                ax_b,
                y - 0.13,
                rel,
                ORANGE,
                "s",
                "relative power (pre-registered)" if c == "ds004584" else None,
                "point",
            )
    for ax in (ax_a, ax_b):
        ax.axvline(0.5, color=INK2, linestyle=(0, (3, 3)), linewidth=1)
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_xlim(0.2, 1.0)
    ax_a.set_yticks(ys, labels)
    ax_a.set_xlabel("ROC-AUC, cohort vs ds007526")
    ax_a.set_title("A  Site identity", loc="left", fontsize=9, fontweight="bold")
    ax_b.set_xlabel("ROC-AUC, PD vs control (95% CI)")
    ax_b.set_title("B  Disease transfer from ds007526", loc="left", fontsize=9, fontweight="bold")
    ax_b.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=2, frameon=False, fontsize=8)
    fig.tight_layout()
    return fig


def fig_robustness() -> plt.Figure:
    rb = _load("clinical_robustness.json")
    rows = [("ADR 0017 reference (age)", rb["base_age_only"])]
    rows += [(name.split(" ", 1)[1], v) for name, v in rb["checks"].items()]
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    n = len(rows)
    ys = [n - i for i in range(n)]
    for y, (_, res) in zip(ys, rows, strict=True):
        for cohort, color, marker, dy in (
            ("ds007526", BLUE, "o", 0.13),
            ("ds004584", ORANGE, "s", -0.13),
        ):
            v = res[cohort]
            _errbar(ax, y + dy, v, color, marker, f"{cohort}" if y == ys[0] else None, "r")
            ax.text(P_COL, y + dy, f"p={v['p']:.3f}", va="center", fontsize=7, color=INK2)
    po = rb["pooled_age_only"]
    ax.errorbar(
        po["r"],
        0,
        xerr=[[po["r"] - po["lo"]], [po["hi"] - po["r"]]],
        fmt="D",
        color=INK,
        elinewidth=2,
        markersize=7,
        markeredgecolor="white",
        label="pooled (Fisher z, age only)",
    )
    ax.axvline(0, color=INK2, linestyle=(0, (3, 3)), linewidth=1)
    ax.axhline(0.5, color=GRID, linewidth=0.8)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_yticks([*ys, 0], [r for r, _ in rows] + ["pooled, both cohorts"])
    ax.set_xlabel("Spearman partial r, global theta/alpha ratio vs MoCA (95% CI)")
    ax.set_xlim(-0.6, 0.3)
    ax.text(P_COL, n + 0.55, "p (two-sided)", fontsize=7, color=INK2, va="center")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False, fontsize=8)
    fig.tight_layout()
    return fig


FIGURES = {
    "fig1_transfer.svg": fig_transfer,
    "fig2_cognition_robustness.svg": fig_robustness,
}


def render(builder) -> bytes:
    buf = io.BytesIO()
    fig = builder()
    fig.savefig(buf, format="svg", metadata={"Date": None})
    plt.close(fig)
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NeuroPD manuscript figures")
    parser.add_argument("--check", action="store_true", help="Fail if a figure is stale.")
    args = parser.parse_args(argv)
    stale = []
    for name, builder in FIGURES.items():
        data = render(builder)
        path = OUT / name
        if args.check:
            if not path.is_file() or path.read_bytes() != data:
                stale.append(name)
        else:
            OUT.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            print(f"Wrote {path}")
    if stale:
        sys.stderr.write(f"stale figures: {stale}; run scripts/generate_figures.py\n")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
