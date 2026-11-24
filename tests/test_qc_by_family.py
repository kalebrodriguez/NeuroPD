"""ADR 0021: QC sensitivity by feature family — rule logic and committed report, offline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
fam = pytest.importorskip("evaluate_qc_by_family")


def _auc(drops: dict[str, float]) -> dict:
    """150 µV AUC 0.8 everywhere; 400 µV lower by each family's drop."""
    out: dict = {}
    for arm, delta in (("150", 0.0), ("200", None), ("400", 1.0)):
        out[arm] = {
            f: {
                c: {"point": 0.8 - (drops[f] * delta if delta is not None else 0.0)}
                for c in fam.EXTERNAL
            }
            for f in drops
        }
    return out


def _drops(**over: float) -> dict[str, float]:
    base = {
        "relative power": 0.01,
        "absolute power": 0.1,
        "log power": 0.1,
        "slowing (paf/sef/ratios)": 0.01,
        "complexity": 0.05,
    }
    return base | over


def test_degradation_is_mean_primary_minus_loosest() -> None:
    assert fam.degradation(_auc(_drops()), "log power") == pytest.approx(0.1)


def test_h5_supported_when_every_sensitive_family_degrades_more() -> None:
    assert fam.apply_rule(_auc(_drops()))["h5_supported"] is True


def test_h5_fails_if_any_invariant_family_degrades_as_much() -> None:
    out = fam.apply_rule(_auc(_drops(**{"relative power": 0.1})))
    assert out["h5_supported"] is False
    out = fam.apply_rule(_auc(_drops(**{"absolute power": -0.02})))
    assert out["h5_supported"] is False


def test_complexity_is_descriptive_only() -> None:
    assert fam.apply_rule(_auc(_drops(complexity=-1.0)))["h5_supported"] is True


def test_committed_report_and_verdict_match_committed_bundle() -> None:
    bundle = json.loads(Path("dashboard/data/qc_by_family.json").read_text())
    assert bundle["adr"] == "0021"
    assert Path("docs/qc_by_family.md").read_text() == fam.render(bundle)
    again = fam.apply_rule(bundle["auc"])
    assert again["h5_supported"] == bundle["h5_supported"]
    assert again["degradation"] == pytest.approx(bundle["degradation"])
