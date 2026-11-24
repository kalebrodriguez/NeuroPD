"""ADR 0020 QC-threshold sensitivity: verdict and rule logic, offline."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
qc = pytest.importorskip("evaluate_qc_threshold")


def _ci(point: float, lo: float) -> dict:
    return {"point": point, "lo": lo, "hi": point + 0.1}


def _arm() -> dict:
    return {
        "transfer_relative_power": {"ds004584": _ci(0.73, 0.64), "ds003490": _ci(0.59, 0.39)},
        "transfer_all": {c: _ci(0.7, 0.5) for c in qc.EXTERNAL},
        "identity": dict.fromkeys(qc.EXTERNAL, 0.92),
        "clinical": {c: {"r": -0.27, "p": 0.008} for c in qc.CLINICAL},
    }


def _arms() -> dict:
    return {a: _arm() for a in qc.ARMS}


def test_robust_when_every_lenient_arm_reproduces_the_verdicts() -> None:
    out = qc.apply_rule(_arms())
    assert out["robust"] is True
    assert set(out["rule"]) == {a for a in qc.ARMS if a != qc.PRIMARY_ARM}


@pytest.mark.parametrize(
    ("mutate", "key"),
    [
        (
            lambda a: a["transfer_relative_power"]["ds004584"].update(lo=0.45),
            "a_h1_verdicts_unchanged",
        ),
        (
            lambda a: a["transfer_relative_power"]["ds003490"].update(lo=0.55),
            "a_h1_verdicts_unchanged",
        ),
        (lambda a: a["identity"].update(ds004584=0.6), "b_identity_exceeds_transfer"),
        (lambda a: a["clinical"]["ds004584"].update(p=0.03), "c_adr0017_unchanged"),
        (lambda a: a["clinical"]["ds007526"].update(r=0.1), "c_adr0017_unchanged"),
    ],
)
def test_each_check_flips_in_one_lenient_arm(mutate, key) -> None:
    arms = _arms()
    mutate(arms["400"])
    out = qc.apply_rule(arms)
    assert out["rule"]["400"][key] is False
    assert all(out["rule"]["200"].values())
    assert out["robust"] is False


def test_primary_arm_is_not_judged_by_the_rule() -> None:
    arms = _arms()
    arms[qc.PRIMARY_ARM] = copy.deepcopy(arms["200"])
    arms[qc.PRIMARY_ARM]["clinical"]["ds004584"]["p"] = 0.5
    assert qc.apply_rule(arms)["robust"] is True


def test_sensitivity_roots_never_point_at_primary_data() -> None:
    lenient = [p for a, p in qc.ARMS.items() if a != qc.PRIMARY_ARM]
    assert qc.ARMS[qc.PRIMARY_ARM] == Path("data/processed")
    assert all(p != qc.ARMS[qc.PRIMARY_ARM] for p in lenient)


def test_committed_report_and_verdict_match_committed_bundle() -> None:
    import json

    bundle = json.loads(Path("dashboard/data/qc_threshold.json").read_text())
    assert bundle["adr"] == "0020"
    assert Path("docs/qc_threshold.md").read_text() == qc.render(bundle)
    again = qc.apply_rule(bundle["arms"])
    assert again["rule"] == bundle["rule"] and again["robust"] == bundle["robust"]
    assert "participants" not in json.dumps(bundle)  # no identifiers in the bundle
