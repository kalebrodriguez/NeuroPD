"""The manuscript draft must be regenerable from committed data and up to date."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_manuscript.py"


def _mod():
    spec = importlib.util.spec_from_file_location("generate_manuscript", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_manuscript_is_up_to_date() -> None:
    assert _mod().main(["--check"]) == 0, "run scripts/generate_manuscript.py"


def test_manuscript_is_deidentified_non_diagnostic_and_cites_only_verified_dois() -> None:
    text = _mod().build()
    assert "participant_id" not in text
    for token in ("sub-pd", "sub-hc", "sub-0", "sub-1"):
        assert token not in text
    assert "nothing here is a diagnostic" in text
    assert "True" not in text and "False" not in text  # no raw booleans leak
    cff = Path("CITATION.cff").read_text()
    for doi in re.findall(r"doi:(10\.\S+?)\)?(?:\s|$)", text):
        assert doi.rstrip(".)") in cff, f"DOI {doi} is not in CITATION.cff"
