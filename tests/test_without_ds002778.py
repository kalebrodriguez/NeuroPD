"""ADR 0019 sensitivity analysis: the rule logic and the committed report, offline."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))
wo = pytest.importorskip("evaluate_without_ds002778")

_DATA = Path("dashboard/data")


def _auc(point: float) -> dict:
    return {"roc_auc": {"point": point, "lo": point - 0.1, "hi": point + 0.1}}


def _payloads(c_at_ds003490: float = 0.6, b_at_ds004584: float = 0.8) -> tuple[dict, ...]:
    arms = {
        "ds007526": {"B": 0.6, "C": 0.6},
        "ds004584": {"A": 0.85, "B": b_at_ds004584, "C": 0.8},
        "ds003490": {"A": 0.5, "B": 0.55, "C": c_at_ds003490},
    }
    loso = {
        "folds": {
            s: {"arms": {a: {"logreg": _auc(v)} for a, v in av.items()}} for s, av in arms.items()
        },
        "h2_supported": False,
    }
    combat = {
        "cohorts": {
            c: {
                "methods": {
                    "none": {"dataset_identity_auc": 0.9, "models": {"logreg": _auc(0.7)}},
                    "combat": {"models": {"logreg": _auc(0.6)}},
                    "combat_agesex": {"models": {"logreg": _auc(0.6)}},
                }
            }
            for c in ("ds004584", "ds003490")
        }
    }
    return loso, copy.deepcopy(loso), combat


def test_rule_unchanged_when_all_checks_hold() -> None:
    out = wo.evaluate(*_payloads())
    assert out["unchanged"] is True
    assert all(out["rule"].values())


def test_rule_flags_each_check_independently() -> None:
    loso, orig, combat = _payloads(c_at_ds003490=0.4)  # arm C no longer beats A
    out = wo.evaluate(loso, orig, combat)
    assert out["rule"]["d_c_beats_a_at_ds003490"] is False
    assert out["unchanged"] is False

    loso, orig, combat = _payloads()
    loso["h2_supported"] = True
    assert wo.evaluate(loso, orig, combat)["rule"]["c_h2_still_not_supported"] is False

    loso, orig, combat = _payloads()
    for c in combat["cohorts"].values():
        c["methods"]["combat"]["models"]["logreg"]["roc_auc"]["point"] = 0.95
    assert wo.evaluate(loso, orig, combat)["rule"]["b_combat_still_not_met"] is False

    loso, orig, combat = _payloads()
    combat["cohorts"]["ds004584"]["methods"]["none"]["dataset_identity_auc"] = 0.6
    assert wo.evaluate(loso, orig, combat)["rule"]["a_identity_exceeds_transfer"] is False


def test_ds002778_excluded_everywhere() -> None:
    assert "ds002778" not in wo.SITES
    assert "ds002778" not in wo.EXTERNAL


def test_committed_report_matches_committed_bundle() -> None:
    bundle = json.loads((_DATA / "without_ds002778.json").read_text())
    assert bundle["adr"] == "0019"
    assert "ds002778" not in bundle["loso"]["n_by_site"]
    assert Path("docs/without_ds002778.md").read_text() == wo.render(bundle)
    # The committed verdict must agree with re-applying the rule to the committed inputs.
    combat = json.loads((_DATA / "combat.json").read_text())
    original = json.loads((_DATA / "multisite.json").read_text())
    again = wo.evaluate(bundle["loso"], original, combat)
    assert again["rule"] == bundle["rule"] and again["unchanged"] == bundle["unchanged"]
