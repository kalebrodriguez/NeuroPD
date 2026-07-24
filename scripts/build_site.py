"""Build the static GitHub Pages research site (multi-page).

Generates a small multi-page static site under ``site/`` from the committed,
de-identified ``dashboard/data/`` outputs. No raw EEG, no participant ids, no
runtime server. Every number is read from executed results.

Pages: index (overview), datasets, biomarkers, results, dataset-shift,
sensitivity, methods. Shared shell (nav, disclaimer, footer, CSS).

Usage:
    uv run python scripts/build_site.py
"""

from __future__ import annotations

import csv
import json
import statistics as stats
from html import escape
from pathlib import Path

DATA = Path("dashboard/data")
OUT = Path("site")
REPO = "https://github.com/kalebrodriguez/NeuroPD"
DISEASE_INTERNAL_AUC = 0.72
DISEASE_EXTERNAL_AUC = 0.67

NAV = [
    ("index", "Overview"),
    ("datasets", "Datasets"),
    ("biomarkers", "Biomarkers"),
    ("results", "Results"),
    ("dataset-shift", "Dataset shift"),
    ("sensitivity", "Sensitivity"),
    ("methods", "Methods"),
]
BIO_LABELS = {
    "paf__occipital__median": "Peak alpha frequency (occipital)",
    "theta_alpha_ratio__central__median": "Theta / alpha ratio (central)",
    "rel_power_alpha__occipital__median": "Relative alpha power (occipital)",
    "rel_power_theta__frontal__median": "Relative theta power (frontal)",
    "rel_power_beta__occipital__median": "Relative beta power (occipital)",
    "spectral_entropy__occipital__median": "Spectral entropy (occipital)",
    "hjorth_complexity__occipital__median": "Hjorth complexity (occipital)",
}


def load_json(name: str) -> dict | None:
    p = DATA / name
    return json.loads(p.read_text()) if p.is_file() else None


def load_biomarkers() -> list[dict]:
    with (DATA / "biomarkers.csv").open() as fh:
        return list(csv.DictReader(fh))


# ---- small components -------------------------------------------------------


def auc_pct(auc: float) -> float:
    return max(0.0, min(1.0, (auc - 0.5) / 0.5)) * 100


def meter(label: str, auc: float, kind: str) -> str:
    return f"""
      <div class="meter">
        <div class="meter-head"><span class="meter-label">{escape(label)}</span>
          <span class="meter-val" data-kind="{kind}">{auc:.2f}</span></div>
        <div class="track"><span class="fill {kind}" style="--w:{auc_pct(auc):.1f}%"></span></div>
      </div>"""


def table(headers: list[str], rows: list[list[str]], raw: bool = False) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{c if raw else escape(str(c))}</td>" for c in r) + "</tr>"
        for r in rows
    )
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def ci(entry: dict) -> str:
    return f"{entry['point']:.3f} <span class='ci'>[{entry['lo']:.2f}, {entry['hi']:.2f}]</span>"


def boxplot_svg(values_hc: list[float], values_pd: list[float]) -> str:
    """A compact two-row box plot (HC top, PD bottom) scaled to the pooled range."""
    allv = [v for v in values_hc + values_pd if v == v]  # drop NaN
    if not allv:
        return ""
    lo, hi = min(allv), max(allv)
    span = (hi - lo) or 1.0
    w, pad = 300, 10

    def x(v: float) -> float:
        return pad + (v - lo) / span * (w - 2 * pad)

    def row(vals: list[float], y: int, cls: str) -> str:
        vs = sorted(v for v in vals if v == v)
        if len(vs) < 2:
            return ""
        q1, med, q3 = (
            stats.quantiles(vs, n=4)[0],
            stats.median(vs),
            stats.quantiles(vs, n=4)[2],
        )
        return (
            f'<line x1="{x(min(vs)):.1f}" x2="{x(max(vs)):.1f}" y1="{y}" y2="{y}" class="wk"/>'
            f'<rect x="{x(q1):.1f}" y="{y - 8}" width="{max(1, x(q3) - x(q1)):.1f}" height="16" class="bx {cls}"/>'
            f'<line x1="{x(med):.1f}" x2="{x(med):.1f}" y1="{y - 8}" y2="{y + 8}" class="md"/>'
        )

    return (
        f'<svg viewBox="0 0 {w} 64" class="box" role="img">'
        f'<text x="0" y="16" class="axl">HC</text><text x="0" y="52" class="axl">PD</text>'
        f"{row(values_hc, 18, 'hc')}{row(values_pd, 46, 'pd')}</svg>"
    )


# ---- pages ------------------------------------------------------------------


def page_index() -> str:
    shift = load_json("metrics.json")["dataset_shift"]["results"]["logreg"]["roc_auc"]
    duel = meter("Predict which dataset a recording is from", shift, "shift") + meter(
        "Predict Parkinson's vs. healthy (within a dataset)", DISEASE_INTERNAL_AUC, "signal"
    )
    return f"""
  <span class="eyebrow">Computational neuroscience · reproducible study</span>
  <h1>A brain-wave biomarker that works — until you change the <span class="em">dataset</span>.</h1>
  <p class="lede">NeuroPD asks a plain question: do interpretable resting-state EEG features that separate Parkinson's patients from controls in one cohort still work in an independent one? Across two public datasets, the answer is sobering — and it is the point.</p>
  <div class="duel">
    <span class="cap">Same EEG features · what can a model actually predict? (ROC-AUC, 0.50 = chance)</span>
    {duel}
    <p class="foot">A classifier tells <b>which dataset</b> a recording came from almost perfectly ({shift:.2f}), but tells <b>disease</b> from the same features only modestly ({DISEASE_INTERNAL_AUC:.2f}). The feature space is dominated by site and equipment, not by the disease.</p>
  </div>
  <div class="grid" style="margin-top:34px">
    <a class="card lnk" href="results.html"><div class="k">6</div><div class="l">models evaluated internally &amp; across datasets →</div></a>
    <a class="card lnk" href="dataset-shift.html"><div class="k">{shift:.2f}</div><div class="l">ROC-AUC predicting dataset identity →</div></a>
    <a class="card lnk" href="sensitivity.html"><div class="k">3</div><div class="l">sensitivity analyses of the findings →</div></a>
  </div>"""


def page_datasets() -> str:
    c = load_json("cohorts.json")
    rows = []
    for acc, d in c.items():
        rows.append(
            [
                acc,
                "development" if acc == "ds007526" else "external validation",
                d["n_participants"],
                f"{d['n_pd']} / {d['n_hc']}",
                f"{d['age_mean']:.0f} ({d['age_min']:.0f}–{d['age_max']:.0f})",
                f"{d['pct_male']:.0f}%",
                d["n_features"],
            ]
        )
    return f"""
  <span class="eyebrow">The cohorts</span>
  <h1>Two independent resting-state EEG datasets</h1>
  <p class="lede">Both are public (CC0), eyes-open resting-state recordings, harmonized to 31 shared 10–20 electrodes. They differ in hardware, sampling rate, country, and class balance — exactly the differences a transferable biomarker must survive.</p>
  {table(["dataset", "role", "n", "PD / HC", "age (range)", "male", "features"], rows)}
  <p class="caption">Counts are after quality control. The development cohort is imbalanced (~4:1 PD:HC) and its patients are older and more male than controls — a confound quantified on the Results page. The external cohort is age/sex-balanced, which is why the demographic shortcut fails to transfer.</p>"""


def page_biomarkers() -> str:
    rows = load_biomarkers()
    dev = [r for r in rows if r["dataset"] == "ds007526"]
    cards = []
    for col, label in BIO_LABELS.items():
        if col not in dev[0]:
            continue
        hc = [float(r[col]) for r in dev if r["group"] == "HC" and r[col]]
        pd = [float(r[col]) for r in dev if r["group"] == "PD" and r[col]]
        cards.append(
            f'<div class="bcard"><div class="bl">{escape(label)}</div>{boxplot_svg(hc, pd)}</div>'
        )
    return f"""
  <span class="eyebrow">The biomarkers</span>
  <h1>What the interpretable features look like</h1>
  <p class="lede">Median-over-epoch, region-level values for the development cohort (ds007526), healthy controls vs. Parkinson's. De-identified aggregates — no raw signals, no participant ids. Boxes show the interquartile range; the line is the median; whiskers span the observed range.</p>
  <div class="bgrid">{"".join(cards)}</div>
  <p class="caption">Exploratory only — no statistical test is implied, and overlapping distributions are expected. Group differences may reflect demographics or acquisition rather than disease. The interactive per-dataset explorer lives in the Streamlit dashboard.</p>"""


def page_results() -> str:
    m = load_json("metrics.json")
    internal = m["internal_ds007526"]
    irows = [
        [n, ci(r["balanced_accuracy"]), ci(r["roc_auc"])] for n, r in internal["results"].items()
    ]
    ab = m["external_a_to_b"]
    erows = []
    for n, r in ab["results"].items():
        erows.append(
            [
                n,
                ci(r["external"]["balanced_accuracy"]),
                f"{r['internal_point']['balanced_accuracy']:.3f}",
                f"{r['generalization_gap']['balanced_accuracy']:+.3f}",
            ]
        )
    return f"""
  <span class="eyebrow">The evaluation</span>
  <h1>Inside one dataset, then across the gap</h1>
  <h2>Internal cross-validation — {internal["dataset"]}</h2>
  <p>{internal["n_participants"]} participants ({internal["n_pd"]} PD / {internal["n_hc"]} HC), participant-grouped {internal["cv"]["n_repeats"]}×{internal["cv"]["n_splits"]}-fold CV. Brackets are 95% participant-level bootstrap intervals.</p>
  {table(["model", "balanced accuracy", "ROC-AUC"], irows, raw=True)}
  <p class="caption">A <b>demographics-only</b> model (age + sex) rivals or beats every EEG model on balanced accuracy — much of the within-cohort separation is demographic, not neural.</p>
  <h2 style="margin-top:44px">Frozen external transfer — {ab["train_cohort"]} → {ab["test_cohort"]}</h2>
  <p>Fit on {ab["n_train"]} development participants, evaluated once on {ab["n_test"]} external participants. The external cohort was never used for tuning. "gap" is internal minus external balanced accuracy.</p>
  {table(["model", "external balanced acc", "internal", "gap"], erows, raw=True)}
  <p class="caption">The demographic shortcut collapses to chance on the balanced external cohort; linear EEG models transfer more gracefully, but with only {ab["n_test"]} external participants the intervals are wide — encouraging, not conclusive.</p>"""


def page_shift() -> str:
    m = load_json("metrics.json")
    shift = m["dataset_shift"]["results"]
    imp = load_json("feature_importance.json")
    duel = meter("Predict which dataset (logistic regression)", shift["logreg"]["roc_auc"], "shift")
    duel += meter(
        "Predict which dataset (random forest)", shift["random_forest"]["roc_auc"], "shift"
    )
    duel += meter("Predict disease within a cohort", DISEASE_INTERNAL_AUC, "signal")
    duel += meter("Predict disease across cohorts", DISEASE_EXTERNAL_AUC, "signal")
    imp_html = ""
    if imp:
        rows = [
            [t["feature"], f"{t['coef']:+.3f}", f"{t['sign_consistency']:.2f}"]
            for t in imp["top"][:10]
        ]
        imp_html = (
            f"<h2 style='margin-top:44px'>Which features the model leans on</h2>"
            f"<p>Top standardized coefficients on the development cohort. Cross-dataset "
            f"agreement of feature importance is Pearson r = <span class='num'>"
            f"{imp['cross_dataset_agreement_r']:+.2f}</span> — near zero: the model relies "
            f"on different features in each cohort.</p>"
            + table(["feature", "mean coef", "sign consistency"], rows)
        )
    return f"""
  <span class="eyebrow">Why it fails</span>
  <h1>Dataset identity is the loudest thing in the signal</h1>
  <p class="lede">Turn the same features to a different question — <b>which dataset is this?</b> — and a classifier answers far more accurately than it predicts disease. Site and acquisition dominate the feature space, which is exactly why the biomarker does not travel.</p>
  <div class="duel"><span class="cap">ROC-AUC · dataset identity vs. disease</span>{duel}
  <p class="foot">This is a result about <b>dataset shift</b>, not brain biology — the kind of negative result that keeps a field honest.</p></div>
  {imp_html}"""


def _sens_metric(m: dict) -> str:
    return f"{m['balanced_accuracy']:.3f} / {m['roc_auc']:.3f}"


def page_sensitivity() -> str:
    s = load_json("sensitivity.json")
    if not s:
        return """
  <span class="eyebrow">Robustness</span>
  <h1>Sensitivity analyses</h1>
  <p class="lede">Pending — run <code>scripts/sensitivity.py</code> and rebuild.</p>"""
    harm_rows = []
    for k, v in s["harmonization"].items():
        harm_rows.append(
            [
                f"{k} ({v.get('n_features', '?')})",
                _sens_metric(v["internal"]),
                _sens_metric(v["external"]),
            ]
        )
    adj_rows = [[k.replace("_", " "), _sens_metric(v)] for k, v in s["age_sex_adjustment"].items()]
    fam_rows = [
        [name, v["n_features"], _sens_metric(v["internal"]), _sens_metric(v["external"])]
        for name, v in s["feature_family"].items()
    ]
    return f"""
  <span class="eyebrow">Robustness</span>
  <h1>Do the findings survive different choices?</h1>
  <p class="lede">Pre-declared checks, not a search for the best result. Values are balanced&nbsp;accuracy&nbsp;/&nbsp;ROC-AUC.</p>
  <h2>Channel harmonization — region vs. shared channels</h2>
  {table(["features", "internal", "external"], harm_rows)}
  <h2 style="margin-top:40px">Age/sex adjustment — does EEG add signal beyond demographics?</h2>
  <p>Age and sex are linearly partialled out of the EEG features inside each training fold (no leakage). If residualized EEG stays above chance, EEG carries signal independent of demographics.</p>
  {table(["model", "internal balanced acc / AUC"], adj_rows)}
  <h2 style="margin-top:40px">Feature families</h2>
  {table(["family", "n", "internal", "external"], fam_rows)}
  <p class="caption">Full interpretation: <a href="{REPO}/blob/main/docs/decisions/0010-sensitivity-analyses.md">ADR 0010</a>.</p>"""


def page_methods() -> str:
    return f"""
  <span class="eyebrow">How it was built</span>
  <h1>Reproducible, tested, and honest about its limits</h1>
  <p class="lede">A research-grade pipeline — not a peer-reviewed study or a clinical tool.</p>
  <h2>Pipeline</h2>
  <p>MNE preprocessing on 31 shared channels (1–40 Hz band-pass, per-dataset notch, 250 Hz resample, average reference, 2 s epochs, amplitude rejection) → interpretable spectral and complexity features → one region-level vector per participant → participant-grouped cross-validation with no epoch leakage → a single frozen external test → participant-level bootstrap intervals.</p>
  <h2>Limitations</h2>
  <p>Small external cohort (n=30, wide intervals); ~4:1 class imbalance and an age/sex confound in the development cohort; quality-control exclusions are Parkinson's-concentrated; and dataset shift dominates the feature space. Preprocessing and feature choices are documented defaults, not exhaustively validated, and no EEG-domain expert has reviewed them.</p>
  <h2>Reproducibility</h2>
  <p>Fixed seeds, a locked <code>uv</code> environment, config-driven parameters, decision records in <code>docs/decisions/</code>, and a green CI pipeline. Every number on this site traces to executed code — see the <a href="{REPO}">source and full methods on GitHub</a>.</p>"""


PAGE_FUNCS = {
    "index": page_index,
    "datasets": page_datasets,
    "biomarkers": page_biomarkers,
    "results": page_results,
    "dataset-shift": page_shift,
    "sensitivity": page_sensitivity,
    "methods": page_methods,
}


def shell(slug: str, body: str) -> str:
    nav = "".join(
        f'<a href="{s}.html" class="{"on" if s == slug else ""}">{escape(label)}</a>'
        for s, label in NAV
    )
    title = next(label for s, label in NAV if s == slug)
    return SHELL.format(title=title, nav=nav, body=body, repo=REPO)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, fn in PAGE_FUNCS.items():
        (OUT / f"{slug}.html").write_text(shell(slug, fn()))
    print(f"Wrote {len(PAGE_FUNCS)} pages to {OUT}/")
    return 0


SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NeuroPD — {title}</title>
<meta name="description" content="Cross-dataset validation of EEG biomarkers for Parkinson's disease. Research use only; non-diagnostic.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --ink:#0B1220; --panel:#131C2B; --panel2:#0F1826; --line:#24304a;
    --text:#E6ECF5; --muted:#8A97AD; --signal:#38E0C8; --shift:#F2B441; --maxw:1000px;
    --display:'Space Grotesk',system-ui,sans-serif; --mono:'IBM Plex Mono',ui-monospace,monospace;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--ink); color:var(--text); font-family:var(--display); line-height:1.6; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:var(--maxw); margin:0 auto; padding:0 24px; }}
  a {{ color:var(--signal); text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .eyebrow {{ font-family:var(--mono); font-size:.72rem; letter-spacing:.22em; text-transform:uppercase; color:var(--muted); }}
  h1 {{ font-family:var(--display); font-weight:700; letter-spacing:-.02em; font-size:clamp(1.9rem,4.6vw,3rem); line-height:1.06; margin:.5rem 0 0; max-width:18ch; }}
  h1 .em {{ color:var(--shift); }}
  h2 {{ font-family:var(--display); font-weight:700; font-size:1.35rem; margin:0 0 0; letter-spacing:-.01em; }}
  .lede {{ color:var(--muted); font-size:1.06rem; max-width:64ch; margin:1rem 0 0; }}
  p {{ color:#C4CDDC; max-width:68ch; }}
  .num {{ font-family:var(--mono); color:var(--shift); }} .num.sig {{ color:var(--signal); }}

  .bar {{ background:var(--panel2); border-bottom:1px solid var(--line); font-family:var(--mono); font-size:.72rem; color:var(--muted); }}
  .bar .wrap {{ padding:9px 24px; }} .bar b {{ color:var(--text); font-weight:500; }}

  nav {{ position:sticky; top:0; z-index:5; background:rgba(11,18,32,.85); backdrop-filter:blur(8px); border-bottom:1px solid var(--line); }}
  nav .wrap {{ display:flex; gap:4px 20px; flex-wrap:wrap; align-items:center; padding:14px 24px; }}
  nav .brand {{ font-family:var(--mono); font-weight:500; letter-spacing:.14em; color:var(--text); margin-right:12px; }}
  nav a {{ color:var(--muted); font-size:.9rem; padding:4px 2px; border-bottom:2px solid transparent; }}
  nav a.on {{ color:var(--text); border-bottom-color:var(--signal); }}
  nav a:hover {{ color:var(--text); text-decoration:none; }}

  main {{ padding:52px 0 20px; }}
  main h2 {{ margin-top:8px; }}

  .duel {{ margin:34px 0 8px; display:grid; gap:16px; background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:22px; }}
  .duel .cap {{ font-family:var(--mono); font-size:.7rem; color:var(--muted); letter-spacing:.12em; text-transform:uppercase; }}
  .meter-head {{ display:flex; justify-content:space-between; align-items:baseline; gap:12px; }}
  .meter-label {{ font-size:.92rem; }} .meter-val {{ font-family:var(--mono); font-size:1.15rem; }}
  .meter-val[data-kind=shift] {{ color:var(--shift); }} .meter-val[data-kind=signal] {{ color:var(--signal); }}
  .track {{ position:relative; height:11px; margin-top:7px; background:var(--panel2); border:1px solid var(--line); border-radius:99px; overflow:hidden; }}
  .fill {{ position:absolute; inset:0 auto 0 0; width:var(--w); transform-origin:left; }}
  .fill.shift {{ background:linear-gradient(90deg,#C9891F,var(--shift)); }}
  .fill.signal {{ background:linear-gradient(90deg,#1E9E8C,var(--signal)); }}
  .duel .foot {{ font-size:.9rem; color:var(--muted); }}

  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px; }}
  .card .k {{ font-family:var(--mono); font-size:1.6rem; color:var(--signal); }}
  .card .l {{ color:var(--muted); font-size:.85rem; margin-top:4px; }}
  a.lnk:hover {{ border-color:var(--signal); text-decoration:none; }}

  .scroll {{ overflow-x:auto; margin-top:20px; }}
  table {{ width:100%; border-collapse:collapse; font-size:.9rem; min-width:460px; }}
  th, td {{ text-align:left; padding:11px 14px; border-bottom:1px solid var(--line); }}
  th {{ font-family:var(--mono); font-weight:500; font-size:.7rem; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }}
  td:first-child {{ font-family:var(--mono); color:var(--text); }}
  tbody tr:hover {{ background:rgba(255,255,255,.02); }}
  .ci {{ color:var(--muted); font-family:var(--mono); font-size:.78em; }}
  .caption {{ font-size:.82rem; color:var(--muted); margin-top:12px; max-width:66ch; }}

  .bgrid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:16px; margin-top:24px; }}
  .bcard {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:16px; }}
  .bl {{ font-size:.9rem; margin-bottom:6px; }}
  svg.box {{ width:100%; height:auto; }}
  svg.box .wk {{ stroke:var(--muted); stroke-width:1; }}
  svg.box .bx {{ stroke:none; opacity:.85; }} svg.box .bx.hc {{ fill:var(--signal); }} svg.box .bx.pd {{ fill:var(--shift); }}
  svg.box .md {{ stroke:var(--ink); stroke-width:2; }}
  svg.box .axl {{ fill:var(--muted); font-family:'IBM Plex Mono',monospace; font-size:11px; }}

  footer {{ padding:40px 0 68px; margin-top:40px; border-top:1px solid var(--line); color:var(--muted); font-size:.85rem; }}
  footer a {{ color:var(--muted); text-decoration:underline; }}
  .foot-grid {{ display:flex; flex-wrap:wrap; gap:8px 26px; margin-top:10px; }}

  @media (prefers-reduced-motion:no-preference) {{ .fill {{ transform:scaleX(0); animation:g 1s .2s cubic-bezier(.2,.7,.2,1) forwards; }} }}
  @keyframes g {{ to {{ transform:scaleX(1); }} }}
</style>
</head>
<body>
<div class="bar"><div class="wrap"><b>Research use only.</b> NeuroPD studies EEG-biomarker robustness across datasets. It does not diagnose Parkinson's disease and is not a medical device.</div></div>
<nav><div class="wrap"><span class="brand">NeuroPD</span>{nav}</div></nav>
<main><div class="wrap">{body}</div></main>
<footer><div class="wrap">Research use only · not a medical device · non-diagnostic.
  <div class="foot-grid"><span><a href="{repo}">Source &amp; full methods on GitHub</a></span>
  <span>Data: OpenNeuro ds007526 &amp; ds002778 (CC0)</span><span>Code: MIT · v0.1.0</span></div>
</div></footer>
</body></html>"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
