"""The consolidated report must be regenerable from committed data and up to date."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_report.py"


def _mod():
    spec = importlib.util.spec_from_file_location("generate_report", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_report_is_up_to_date_with_committed_results() -> None:
    assert _mod().main(["--check"]) == 0, "run scripts/generate_report.py"


def test_report_is_deidentified_and_non_diagnostic() -> None:
    text = _mod().build()
    assert "participant_id" not in text
    for token in ("sub-pd", "sub-hc", "sub-0", "sub-1"):
        assert token not in text
    assert "nothing here is a diagnostic or prognostic claim" in text
