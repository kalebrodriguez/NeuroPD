"""NeuroPD educational dashboard (scaffold, Milestone 7).

The dashboard is built only after the validated analysis pipeline works
(spec Section 17). It is educational and research-oriented, uses only derived,
de-identified results, and must never accept patient data for diagnosis. A
research-only, non-diagnostic disclaimer is displayed prominently.

Run (once implemented): ``uv run streamlit run dashboard/app.py``
"""

from __future__ import annotations

DISCLAIMER = (
    "NeuroPD is a research tool for studying cross-dataset EEG biomarker "
    "robustness. It does NOT diagnose Parkinson's disease and is not for clinical use."
)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="NeuroPD", layout="wide")
    st.title("NeuroPD")
    st.warning(DISCLAIMER)
    st.info(
        "Dashboard content is added in Milestone 7 once the validated analysis "
        "pipeline and derived results exist."
    )


if __name__ == "__main__":  # pragma: no cover
    main()
