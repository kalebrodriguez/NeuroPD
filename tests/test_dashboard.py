"""Dashboard smoke tests (spec Section 17, Section 18.2).

Runs the Streamlit app headlessly against the committed, de-identified
``dashboard/data/`` (no raw EEG, no participant ids) and asserts every page
renders without raising and that the non-diagnostic disclaimer is present.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

DATA = Path("dashboard/data")
APP = Path("dashboard/app.py")


def test_committed_dashboard_data_is_deidentified() -> None:
    with (DATA / "biomarkers.csv").open() as fh:
        header = next(csv.reader(fh))
    # No participant identifier may be present in committed dashboard data.
    assert "participant_id" not in header
    assert {"dataset", "group"} <= set(header)


def test_static_site_is_deidentified_and_disclaimed() -> None:
    site = Path("site/index.html")
    if not site.is_file():
        pytest.skip("site/index.html not generated yet")
    html = site.read_text()
    assert "Research use only" in html
    assert "participant_id" not in html
    # No participant identifier tokens leaked into the published page.
    for token in ("sub-pd", "sub-hc", "sub-0", "sub-1"):
        assert token not in html


@pytest.mark.parametrize(
    "page",
    [
        "Overview",
        "Dataset explorer",
        "Biomarker explorer",
        "Model evaluation",
        "Generalization gap & shift",
        "Methods & limitations",
    ],
)
def test_each_page_renders(page: str) -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=30)
    at.run()
    assert not at.exception
    # Disclaimer is always shown in the sidebar.
    assert any("Research use only" in w.value for w in at.sidebar.warning)
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception
