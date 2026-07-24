"""NeuroPD educational dashboard (Milestone 7, spec Section 17).

Educational, research-oriented dashboard that communicates the cross-dataset
EEG-biomarker results. It reads ONLY committed, de-identified derived outputs from
``dashboard/data/`` (built by ``scripts/build_dashboard_data.py``) — never raw EEG,
never participant identifiers — and never accepts patient data or makes a
diagnosis. A research-only, non-diagnostic disclaimer is shown on every page.

Run: ``uv run streamlit run dashboard/app.py``
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"
DISCLAIMER = (
    "**Research use only.** NeuroPD studies whether EEG biomarkers of Parkinson's "
    "disease generalize across datasets. It does **not** diagnose Parkinson's "
    "disease, is **not** a medical device, and must not be used for clinical decisions."
)
METRIC_LABEL = {
    "balanced_accuracy": "Balanced accuracy",
    "roc_auc": "ROC-AUC",
    "sensitivity": "Sensitivity",
    "specificity": "Specificity",
    "f1": "F1",
}


@st.cache_data
def load_json(name: str) -> dict:
    return json.loads((DATA / name).read_text())


@st.cache_data
def load_biomarkers() -> pd.DataFrame:
    return pd.read_csv(DATA / "biomarkers.csv")


def _point_ci(entry: dict) -> str:
    return f"{entry['point']:.3f} [{entry['lo']:.3f}, {entry['hi']:.3f}]"


def page_overview() -> None:
    st.header("Cross-dataset EEG biomarkers for Parkinson's disease")
    st.markdown(
        "**Research question:** which interpretable resting-state EEG features "
        "associated with Parkinson's disease remain reliable across *independent* "
        "datasets? Performance within one cohort often fails to transfer to another "
        "recorded on different hardware, montage, and population."
    )
    shift = load_json("metrics.json")["dataset_shift"]
    if shift:
        auc = shift["results"]["logreg"]["roc_auc"]
        st.subheader("Headline finding")
        st.markdown(
            f"**Dataset identity is predicted at ROC-AUC ~ {auc:.2f}** from the same "
            "EEG features — far more accurately than disease (~0.72 within-cohort, "
            "~0.65 across cohorts). The shared feature space is dominated by "
            "site/acquisition differences, not disease physiology, which explains the "
            "limited cross-cohort transfer. This is a dataset-shift result, **not** a "
            "biological or clinical claim."
        )
    st.info(
        "Use the sidebar to explore cohorts, biomarkers, model evaluation, and the "
        "generalization gap."
    )


def page_datasets() -> None:
    st.header("Dataset explorer")
    cohorts = load_json("cohorts.json")
    rows = []
    for acc, c in cohorts.items():
        rows.append(
            {
                "dataset": acc,
                "role": "development" if acc == "ds007526" else "external validation",
                "participants": c["n_participants"],
                "PD": c["n_pd"],
                "HC": c["n_hc"],
                "age mean [range]": f"{c['age_mean']:.1f} [{c['age_min']:.0f}-{c['age_max']:.0f}]",
                "% male": f"{c['pct_male']:.0f}",
                "features": c["n_features"],
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption(
        "Both cohorts are resting-state, eyes-open, harmonized to 31 shared 10-20 "
        "channels. Counts are post-quality-control (see docs/preprocessing_qc.md). "
        "ds007526 is imbalanced (~4:1 PD:HC) and its PD are older and more male — a "
        "confound examined in Model evaluation."
    )


def page_biomarkers() -> None:
    st.header("Biomarker explorer")
    st.markdown(
        "Distributions of interpretable EEG features by group, per dataset. These are "
        "median-over-epoch, region-level, de-identified values (no participant ids)."
    )
    bio = load_biomarkers()
    feature_cols = [c for c in bio.columns if c not in ("dataset", "group")]
    labels = {c: c.replace("__", " · ").replace("_", " ") for c in feature_cols}
    choice = st.selectbox("Feature", feature_cols, format_func=lambda c: labels[c])
    dataset = st.radio("Dataset", sorted(bio["dataset"].unique()), horizontal=True)
    sub = bio[bio["dataset"] == dataset]
    n_pd = int((sub["group"] == "PD").sum())
    n_hc = int((sub["group"] == "HC").sum())
    st.caption(f"n = {len(sub)} participants ({n_pd} PD / {n_hc} HC)")

    import plotly.express as px

    fig = px.box(
        sub,
        x="group",
        y=choice,
        color="group",
        points="all",
        category_orders={"group": ["HC", "PD"]},
        labels={choice: labels[choice], "group": "Group"},
    )
    fig.update_layout(showlegend=False, height=440)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"Box plot of {labels[choice]} by group in {dataset}. Exploratory only — no "
        "statistical test is implied; group differences may reflect demographics or "
        "acquisition, not disease."
    )


def _metric_table(models: dict, extract) -> pd.DataFrame:
    rows = []
    for name, res in models.items():
        row = {"model": name}
        row.update(extract(res))
        rows.append(row)
    return pd.DataFrame(rows)


def page_evaluation() -> None:
    st.header("Model evaluation")
    metrics = load_json("metrics.json")
    internal = metrics["internal_ds007526"]
    if internal:
        st.subheader(f"Internal cross-validation — {internal['dataset']}")
        st.caption(
            f"{internal['n_participants']} participants ({internal['n_pd']} PD / "
            f"{internal['n_hc']} HC), {internal['n_features']} features, "
            f"{internal['cv']['n_repeats']}x stratified grouped "
            f"{internal['cv']['n_splits']}-fold CV. 95% participant-level bootstrap CIs."
        )
        df = _metric_table(
            internal["results"],
            lambda r: {METRIC_LABEL[k]: _point_ci(r[k]) for k in ("balanced_accuracy", "roc_auc")},
        )
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.info(
            "The **demographics-only** (age + sex) model rivals or beats the EEG models "
            "on balanced accuracy — evidence of age/sex confounding within this cohort. "
            "Compare EEG rows against it before interpreting EEG performance."
        )


def page_generalization() -> None:
    st.header("Generalization gap & dataset shift")
    metrics = load_json("metrics.json")
    ab = metrics["external_a_to_b"]
    if ab:
        st.subheader(f"External transfer — {ab['train_cohort']} -> {ab['test_cohort']}")
        st.caption(
            f"Fit on {ab['n_train']} development participants, evaluated once on "
            f"{ab['n_test']} external participants. The external cohort was never used "
            "for tuning."
        )
        rows = []
        for name, r in ab["results"].items():
            rows.append(
                {
                    "model": name,
                    "external balanced acc": _point_ci(r["external"]["balanced_accuracy"]),
                    "external ROC-AUC": _point_ci(r["external"]["roc_auc"]),
                    "internal balanced acc": f"{r['internal_point']['balanced_accuracy']:.3f}",
                    "gap (bal acc)": f"{r['generalization_gap']['balanced_accuracy']:+.3f}",
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.markdown(
            "The **demographic confound does not transfer** (balanced accuracy falls to "
            "chance on the balanced external cohort); linear EEG models transfer modestly "
            "but the small external cohort gives wide, inconclusive intervals."
        )

    shift = metrics["dataset_shift"]
    if shift:
        st.subheader("Unsupervised dataset-shift test")
        import plotly.express as px

        comp = pd.DataFrame(
            {
                "task": [
                    "Predict DATASET identity",
                    "Predict DISEASE (internal)",
                    "Predict DISEASE (external)",
                ],
                "ROC-AUC": [shift["results"]["logreg"]["roc_auc"], 0.72, 0.67],
            }
        )
        fig = px.bar(comp, x="task", y="ROC-AUC", range_y=[0.5, 1.0], text="ROC-AUC")
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig.update_layout(height=420, xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Dataset identity is far easier to predict than disease — the feature space "
            "is dominated by site/acquisition differences. Disease AUCs (0.72 / 0.67) are "
            "reference points from the internal and external evaluations."
        )


def page_methods() -> None:
    st.header("Methods & limitations")
    st.markdown(
        "- **Pipeline:** MNE preprocessing (31 shared channels, 1-40 Hz, notch, 250 Hz, "
        "average reference, 2 s epochs, amplitude rejection) → interpretable spectral + "
        "complexity features → one region-level vector per participant.\n"
        "- **Validation:** participant-grouped cross-validation (no epoch leakage); a "
        "single frozen external evaluation; participant-level bootstrap CIs.\n"
        "- **Limitations:** small external cohort (n=30, wide CIs); ~4:1 class imbalance "
        "and an age/sex confound in the development cohort; QC exclusions are "
        "PD-concentrated; dataset shift dominates the feature space.\n"
        "- **Reproducibility:** fixed seeds, `uv` lockfile, config-driven parameters, "
        "and decision records in `docs/decisions/`."
    )
    st.caption("Full detail: docs/dataset_audit.md, docs/limitations.md, docs/decisions/.")


PAGES = {
    "Overview": page_overview,
    "Dataset explorer": page_datasets,
    "Biomarker explorer": page_biomarkers,
    "Model evaluation": page_evaluation,
    "Generalization gap & shift": page_generalization,
    "Methods & limitations": page_methods,
}


def main() -> None:
    st.set_page_config(page_title="NeuroPD", layout="wide")
    st.sidebar.title("NeuroPD")
    st.sidebar.warning(DISCLAIMER)
    choice = st.sidebar.radio("Page", list(PAGES))
    PAGES[choice]()


if __name__ == "__main__":  # pragma: no cover
    main()
