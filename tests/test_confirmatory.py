"""Tests for the pre-registered confirmatory analysis (ADR 0013), offline."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from neuropd.features.families import FAMILIES, PRIMARY_FAMILY, family_columns

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_confirmatory.py"


def _script():
    spec = importlib.util.spec_from_file_location("evaluate_confirmatory", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


COLS = [
    "rel_power_alpha__frontal__median",
    "abs_power_alpha__frontal__median",
    "log_power_alpha__frontal__median",
    "paf__frontal__median",
    "perm_entropy__frontal__iqr",
    "rel_power_theta__occipital__iqr",
    "aperiodic_exponent__frontal__median",
]


def test_primary_family_is_relative_power_only() -> None:
    assert PRIMARY_FAMILY == "relative power"
    assert family_columns(COLS, PRIMARY_FAMILY) == [
        "rel_power_alpha__frontal__median",
        "rel_power_theta__occipital__iqr",
    ]


def test_families_are_disjoint() -> None:
    seen: set[str] = set()
    for fam in FAMILIES:
        cols = set(family_columns(COLS, fam))
        assert not cols & seen
        seen |= cols


def test_h1_decision_rule_is_strict_lower_bound() -> None:
    mod = _script()
    assert mod.h1_confirmed(0.51)
    assert not mod.h1_confirmed(0.50)
    assert not mod.h1_confirmed(0.42)


def test_render_reports_verdict_and_disclaimer() -> None:
    mod = _script()
    ci = {"point": 0.7, "lo": 0.6, "hi": 0.8}
    ext = {k: ci for k in mod.METRIC_KEYS}
    payload = {
        "train_cohort": "ds007526",
        "test_cohort": "ds004584",
        "generated_utc": "2026-11-08T00:00:00+00:00",
        "n_train": 144,
        "n_test": 149,
        "n_test_pd": 100,
        "n_features": 230,
        "primary": {"external": ext, "confirmed": True},
        "baselines": {"logreg": {"external": ext, "calibration": {"brier": 0.2}}},
        "families": {"relative power": {"external": ext, "n_features": 40}},
        "dataset_identity": {"logreg": {"balanced_accuracy": 0.9, "roc_auc": 0.95}},
    }
    md = mod.render([payload])
    assert "| ds004584 | 149 (100) | 0.700 [0.600, 0.800]" in md
    assert "**confirmed**" in md
    assert "not a diagnostic test" in md


def test_render_includes_sensitivity_rows() -> None:
    mod = _script()
    ci = {"point": 0.55, "lo": 0.45, "hi": 0.65}
    ext = {k: ci for k in mod.METRIC_KEYS}
    base = {
        "train_cohort": "ds007526",
        "test_cohort": "ds004584",
        "generated_utc": "x",
        "n_train": 1,
        "n_test": 1,
        "n_test_pd": 1,
        "n_features": 1,
        "primary": {"external": ext, "confirmed": False},
        "baselines": {},
        "families": {},
        "dataset_identity": {},
    }
    sens = {**base, "feature_suffix": "_excl-PO3-PO4"}
    md = mod.render([base], [sens])
    assert "| ds004584 | `excl-PO3-PO4` | 0.550 [0.450, 0.650]" in md
    assert "**not confirmed**" in md
