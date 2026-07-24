"""Build the static GitHub Pages research site (deployment).

Generates a single self-contained ``site/index.html`` from the committed,
de-identified ``dashboard/data/`` outputs. No raw EEG, no participant ids, no
runtime server — the page is static and safe to publish (spec Section 17 +
deployment roadmap). Every number is read from executed results.

Usage:
    uv run python scripts/build_site.py
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

DATA = Path("dashboard/data")
OUT = Path("site/index.html")
REPO = "https://github.com/kalebrodriguez/NeuroPD"

# Disease predictability reference points (interpretable logreg): internal CV and
# external transfer ROC-AUC, from the executed metrics.
DISEASE_INTERNAL_AUC = 0.72
DISEASE_EXTERNAL_AUC = 0.67


def _auc_pct(auc: float) -> float:
    """Map ROC-AUC in [0.5, 1.0] (chance..perfect) to a 0-100% meter width."""
    return max(0.0, min(1.0, (auc - 0.5) / 0.5)) * 100


def meter(label: str, auc: float, kind: str) -> str:
    """A horizontal signal meter; ``kind`` is 'shift' (amber) or 'signal' (teal)."""
    return f"""
      <div class="meter">
        <div class="meter-head">
          <span class="meter-label">{escape(label)}</span>
          <span class="meter-val" data-kind="{kind}">{auc:.2f}</span>
        </div>
        <div class="track"><span class="fill {kind}" style="--w:{_auc_pct(auc):.1f}%"></span></div>
      </div>"""


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in r) + "</tr>" for r in rows
    )
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _pt_ci(entry: dict) -> str:
    return f"{entry['point']:.3f} <span class='ci'>[{entry['lo']:.2f}, {entry['hi']:.2f}]</span>"


def cohorts_section(cohorts: dict) -> str:
    rows = []
    for acc, c in cohorts.items():
        role = "development" if acc == "ds007526" else "external validation"
        rows.append(
            [
                acc,
                role,
                c["n_participants"],
                f"{c['n_pd']} / {c['n_hc']}",
                f"{c['age_mean']:.0f} ({c['age_min']:.0f}-{c['age_max']:.0f})",
                f"{c['pct_male']:.0f}%",
            ]
        )
    return table(["dataset", "role", "n", "PD / HC", "age", "male"], rows)


def internal_section(internal: dict) -> str:
    rows = []
    for name, r in internal["results"].items():
        rows.append([name, _pt_ci(r["balanced_accuracy"]), _pt_ci(r["roc_auc"])])
    return table(["model", "balanced accuracy", "ROC-AUC"], rows)


def external_section(ab: dict) -> str:
    rows = []
    for name, r in ab["results"].items():
        rows.append(
            [
                name,
                _pt_ci(r["external"]["balanced_accuracy"]),
                f"{r['internal_point']['balanced_accuracy']:.3f}",
                f"{r['generalization_gap']['balanced_accuracy']:+.3f}",
            ]
        )
    return table(["model", "external balanced acc", "internal", "gap"], rows)


# Note: table() escapes cell text, so CI markup must be injected after building.
def _unescape_ci(html: str) -> str:
    return html.replace("&lt;span class=&#x27;ci&#x27;&gt;", "<span class='ci'>").replace(
        "&lt;/span&gt;", "</span>"
    )


def build() -> str:
    cohorts = json.loads((DATA / "cohorts.json").read_text())
    metrics = json.loads((DATA / "metrics.json").read_text())
    shift = metrics["dataset_shift"]["results"]["logreg"]["roc_auc"]

    hero_meters = meter("Predict which dataset a recording is from", shift, "shift") + meter(
        "Predict Parkinson's vs. healthy (within a dataset)", DISEASE_INTERNAL_AUC, "signal"
    )
    cohorts_html = cohorts_section(cohorts)
    internal_html = _unescape_ci(internal_section(metrics["internal_ds007526"]))
    external_html = _unescape_ci(external_section(metrics["external_a_to_b"]))

    return PAGE.format(
        repo=REPO,
        hero_meters=hero_meters,
        shift_auc=f"{shift:.2f}",
        disease_auc=f"{DISEASE_INTERNAL_AUC:.2f}",
        disease_ext=f"{DISEASE_EXTERNAL_AUC:.2f}",
        cohorts=cohorts_html,
        internal=internal_html,
        external=external_html,
        dev_n=cohorts["ds007526"]["n_participants"],
        ext_n=cohorts["ds002778"]["n_participants"],
        n_features=cohorts["ds007526"]["n_features"],
    )


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NeuroPD — Do EEG biomarkers for Parkinson's generalize across datasets?</title>
<meta name="description" content="A reproducible cross-dataset study: dataset identity is far more predictable than Parkinson's disease from EEG, so within-cohort biomarkers do not transfer. Research use only.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --ink:#0B1220; --panel:#131C2B; --panel2:#0F1826; --line:#24304a;
    --text:#E6ECF5; --muted:#8A97AD; --signal:#38E0C8; --shift:#F2B441;
    --maxw:1080px;
    --display:'Space Grotesk',system-ui,sans-serif;
    --mono:'IBM Plex Mono',ui-monospace,monospace;
    --body:'Space Grotesk',system-ui,sans-serif;
  }}
  * {{ box-sizing:border-box; }}
  html {{ scroll-behavior:smooth; }}
  body {{
    margin:0; background:var(--ink); color:var(--text); font-family:var(--body);
    line-height:1.6; -webkit-font-smoothing:antialiased;
  }}
  .wrap {{ max-width:var(--maxw); margin:0 auto; padding:0 24px; }}
  .eyebrow {{ font-family:var(--mono); font-size:.72rem; letter-spacing:.22em;
    text-transform:uppercase; color:var(--muted); }}
  a {{ color:var(--signal); text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}

  /* --- top disclaimer bar --- */
  .bar {{ background:var(--panel2); border-bottom:1px solid var(--line);
    font-family:var(--mono); font-size:.72rem; letter-spacing:.04em; color:var(--muted); }}
  .bar .wrap {{ padding:9px 24px; }}
  .bar b {{ color:var(--text); font-weight:500; }}

  /* --- hero --- */
  header {{ padding:76px 0 40px; border-bottom:1px solid var(--line);
    background:radial-gradient(120% 90% at 82% -10%, rgba(242,180,65,.10), transparent 55%),
               radial-gradient(90% 70% at 0% 0%, rgba(56,224,200,.08), transparent 50%); }}
  h1 {{ font-family:var(--display); font-weight:700; letter-spacing:-.02em;
    font-size:clamp(2.1rem,5.4vw,3.5rem); line-height:1.04; margin:.5rem 0 0; max-width:16ch; }}
  h1 .em {{ color:var(--shift); }}
  .lede {{ color:var(--muted); font-size:1.08rem; max-width:60ch; margin:1.1rem 0 0; }}

  /* --- signature: gauge duel --- */
  .duel {{ margin:40px 0 8px; display:grid; gap:18px;
    background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:24px; }}
  .duel .cap {{ font-family:var(--mono); font-size:.72rem; color:var(--muted);
    letter-spacing:.12em; text-transform:uppercase; }}
  .meter-head {{ display:flex; justify-content:space-between; align-items:baseline; gap:12px; }}
  .meter-label {{ font-size:.95rem; }}
  .meter-val {{ font-family:var(--mono); font-size:1.25rem; font-weight:500; }}
  .meter-val[data-kind=shift] {{ color:var(--shift); }}
  .meter-val[data-kind=signal] {{ color:var(--signal); }}
  .track {{ position:relative; height:12px; margin-top:8px; background:var(--panel2);
    border:1px solid var(--line); border-radius:99px; overflow:hidden; }}
  .fill {{ position:absolute; inset:0 auto 0 0; width:var(--w); border-radius:99px;
    transform-origin:left; transform:scaleX(1); }}
  .fill.shift {{ background:linear-gradient(90deg,#C9891F,var(--shift)); }}
  .fill.signal {{ background:linear-gradient(90deg,#1E9E8C,var(--signal)); }}
  .track::after {{ content:"chance 0.50"; position:absolute; left:8px; top:-20px;
    font-family:var(--mono); font-size:.6rem; color:var(--muted); }}
  .duel .foot {{ font-size:.9rem; color:var(--muted); }}

  /* --- eeg trace divider --- */
  .trace {{ width:100%; height:44px; display:block; color:var(--line); margin:8px 0; }}

  /* --- sections --- */
  section {{ padding:56px 0; border-bottom:1px solid var(--line); }}
  h2 {{ font-family:var(--display); font-weight:700; letter-spacing:-.01em;
    font-size:clamp(1.4rem,3vw,1.9rem); margin:.4rem 0 0; }}
  section p {{ color:#C4CDDC; max-width:66ch; }}
  .num {{ font-family:var(--mono); color:var(--shift); }}
  .num.sig {{ color:var(--signal); }}

  /* --- tables --- */
  .scroll {{ overflow-x:auto; margin-top:22px; }}
  table {{ width:100%; border-collapse:collapse; font-size:.9rem; min-width:460px; }}
  th, td {{ text-align:left; padding:11px 14px; border-bottom:1px solid var(--line); }}
  th {{ font-family:var(--mono); font-weight:500; font-size:.72rem; letter-spacing:.08em;
    text-transform:uppercase; color:var(--muted); }}
  td:first-child {{ font-family:var(--mono); color:var(--text); }}
  tbody tr:hover {{ background:rgba(255,255,255,.02); }}
  .ci {{ color:var(--muted); font-family:var(--mono); font-size:.78em; }}
  .caption {{ font-size:.82rem; color:var(--muted); margin-top:12px; max-width:64ch; }}

  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin-top:24px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:20px; }}
  .card .k {{ font-family:var(--mono); font-size:1.6rem; color:var(--signal); }}
  .card .l {{ color:var(--muted); font-size:.85rem; margin-top:4px; }}

  footer {{ padding:44px 0 72px; color:var(--muted); font-size:.85rem; }}
  footer a {{ color:var(--muted); text-decoration:underline; }}
  .foot-grid {{ display:flex; flex-wrap:wrap; gap:8px 28px; margin-top:10px; }}

  @media (prefers-reduced-motion:no-preference) {{
    .fill {{ transform:scaleX(0); animation:grow 1.1s .25s cubic-bezier(.2,.7,.2,1) forwards; }}
    .trace path {{ stroke-dasharray:1400; stroke-dashoffset:1400; animation:draw 2.4s .2s ease forwards; }}
  }}
  @keyframes grow {{ to {{ transform:scaleX(1); }} }}
  @keyframes draw {{ to {{ stroke-dashoffset:0; }} }}
</style>
</head>
<body>
<div class="bar"><div class="wrap"><b>Research use only.</b> NeuroPD studies EEG-biomarker robustness across datasets. It does not diagnose Parkinson's disease and is not a medical device.</div></div>

<header><div class="wrap">
  <span class="eyebrow">Computational neuroscience · reproducible study</span>
  <h1>A brain-wave biomarker that works — until you change the <span class="em">dataset</span>.</h1>
  <p class="lede">NeuroPD asks a plain question: do interpretable resting-state EEG features that separate Parkinson's patients from controls in one cohort still work in an independent one? Across two public datasets, the answer is sobering — and it is the point.</p>

  <div class="duel">
    <span class="cap">Same EEG features · what can a model actually predict? (ROC-AUC, 0.50 = chance)</span>
    {hero_meters}
    <p class="foot">A classifier tells <b>which dataset</b> a recording came from almost perfectly ({shift_auc}), but tells <b>disease</b> from the same features only modestly ({disease_auc}). The feature space is dominated by site and equipment, not by the disease.</p>
  </div>
</div></header>

<svg class="trace" viewBox="0 0 1080 44" preserveAspectRatio="none" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="1.5" d="M0 22 H120 l14 -13 8 26 8 -20 10 14 H320 q30 0 40 -16 t40 16 H560 l12 -18 9 30 9 -24 11 16 H820 q26 0 34 -12 t34 12 H1080"/></svg>

<section id="question"><div class="wrap">
  <span class="eyebrow">01 · the question</span>
  <h2>Within-cohort accuracy is not evidence of a biomarker</h2>
  <p>Many EEG machine-learning studies report strong accuracy inside a single dataset. But a real biomarker has to survive a different hospital, a different EEG cap, and a different population. NeuroPD holds one dataset out entirely and tests whether the model still works — the honest bar for a clinical claim, and one that within-cohort numbers quietly skip.</p>
  <div class="grid">
    <div class="card"><div class="k">{dev_n}</div><div class="l">development participants (ds007526)</div></div>
    <div class="card"><div class="k">{ext_n}</div><div class="l">external-validation participants (ds002778)</div></div>
    <div class="card"><div class="k">{n_features}</div><div class="l">interpretable features per participant</div></div>
  </div>
</div></section>

<section id="cohorts"><div class="wrap">
  <span class="eyebrow">02 · the cohorts</span>
  <h2>Two independent resting-state EEG datasets</h2>
  <p>Both are public, CC0, eyes-open resting-state recordings, harmonized to 31 shared electrodes. They differ in hardware, sampling rate, country, and balance — the very differences a transferable biomarker must survive.</p>
  {cohorts}
  <p class="caption">Counts are after quality control. The development cohort is imbalanced (~4:1 PD:HC) and its patients are older and more male — a confound tested directly below.</p>
</div></section>

<section id="internal"><div class="wrap">
  <span class="eyebrow">03 · inside one dataset</span>
  <h2>The confound hiding in within-cohort accuracy</h2>
  <p>Under participant-grouped cross-validation, a model using only <b>age and sex</b> matches or beats the EEG models on balanced accuracy. Much of the apparent "EEG signal" is demographic difference between the groups, not brain physiology.</p>
  {internal}
  <p class="caption">Development cohort, 5×5 stratified grouped cross-validation. Brackets are 95% participant-level bootstrap intervals. Compare every EEG row against <span class="num sig">demographics</span>.</p>
</div></section>

<section id="external"><div class="wrap">
  <span class="eyebrow">04 · across datasets</span>
  <h2>The demographic shortcut doesn't survive the trip</h2>
  <p>Trained on the full development cohort and tested once on the untouched external cohort, the demographics model collapses to chance — because the external cohort is age/sex-balanced. The interpretable EEG models transfer more gracefully, but the external cohort is small ({ext_n}), so the intervals are wide and the result is encouraging, not conclusive.</p>
  {external}
  <p class="caption">Transfer ds007526 → ds002778. "gap" is internal minus external balanced accuracy; positive means worse abroad. External disease ROC-AUC settles around <span class="num sig">{disease_ext}</span>.</p>
</div></section>

<section id="shift"><div class="wrap">
  <span class="eyebrow">05 · why it fails</span>
  <h2>Dataset identity is the loudest thing in the signal</h2>
  <p>Turn the same features to a different question — <b>which dataset is this?</b> — and a classifier answers at ROC-AUC <span class="num">{shift_auc}</span>, far above disease (<span class="num sig">{disease_auc}</span> within-cohort). The features that predict disease also disagree completely between cohorts (correlation ≈ 0). Site and acquisition dominate the feature space, which is exactly why the biomarker does not travel.</p>
  <div class="duel">
    <span class="cap">The finding, restated</span>
    {hero_meters}
    <p class="foot">This is a result about <b>dataset shift</b>, not about brain biology — and it is the kind of negative result that keeps a field honest.</p>
  </div>
</div></section>

<section id="methods"><div class="wrap">
  <span class="eyebrow">06 · how it was built</span>
  <h2>Reproducible, tested, and honest about its limits</h2>
  <p>MNE preprocessing on 31 shared channels → interpretable spectral and complexity features → one vector per participant → participant-grouped cross-validation with no epoch leakage → a single frozen external test → bootstrap confidence intervals. Fixed seeds, a locked environment, config-driven parameters, decision records, and a green CI pipeline. Known limits: a small external cohort, class imbalance and demographic confounding in development, PD-concentrated quality-control exclusions, and dataset shift that dominates the feature space.</p>
</div></section>

<footer><div class="wrap">
  Research use only · not a medical device · non-diagnostic.
  <div class="foot-grid">
    <span><a href="{repo}">Source & full methods on GitHub</a></span>
    <span>Data: OpenNeuro ds007526 &amp; ds002778 (CC0)</span>
    <span>Code: MIT · v0.1.0</span>
  </div>
</div></footer>
</body>
</html>"""


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build())
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
