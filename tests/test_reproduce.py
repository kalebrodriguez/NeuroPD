"""Reproduction verifier: comparison and normalization logic, offline."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
rep = pytest.importorskip("reproduce")


def test_timestamps_are_ignored_but_numbers_are_not() -> None:
    a = {"generated_utc": "2026-11-08T03:00:00+00:00", "auc": {"point": 0.733}}
    b = {"generated_utc": "2026-11-24T21:00:00+00:00", "auc": {"point": 0.733}}
    assert rep.compare(a, b, "x").status == "match"
    b["auc"]["point"] = 0.734
    check = rep.compare(a, b, "x")
    assert check.status == "differs"
    assert "/auc/point" in check.detail


def test_numeric_diffs_reports_missing_keys_and_lengths() -> None:
    diffs = dict(rep.numeric_diffs({"a": [1, 2], "b": 1}, {"a": [1], "c": 1}))
    assert diffs["/a"].startswith("length")
    assert diffs["/b"] == "missing on one side"
    assert diffs["/c"] == "missing on one side"


def test_nested_volatile_keys_are_stripped() -> None:
    obj = {"loso": {"generated_utc": "t", "folds": [{"generated_utc": "t", "v": 1}]}}
    assert rep.strip_volatile(obj) == {"loso": {"folds": [{"v": 1}]}}


def test_text_normalization_only_masks_timestamps() -> None:
    a = "Generated on 2026-11-24T21:17:22+00:00. AUC 0.733."
    b = "Generated on 2026-12-01T09:00:00+00:00. AUC 0.733."
    assert rep.normalize_text(a) == rep.normalize_text(b)
    assert rep.normalize_text(a) != rep.normalize_text(b.replace("0.733", "0.734"))


def test_every_committed_bundle_has_a_producing_stage() -> None:
    produced = {
        "sensitivity.json": "sensitivity",
        "feature_importance.json": "explain",
        "combat.json": "evaluate_combat",
        "aperiodic_specparam.json": "evaluate_aperiodic",
        "multisite.json": "evaluate_multisite",
        "clinical.json": "evaluate_clinical",
        "clinical_robustness.json": "evaluate_clinical_robustness",
        "without_ds002778.json": "evaluate_without_ds002778",
        "qc_threshold.json": "evaluate_qc_threshold",
        "qc_by_family.json": "evaluate_qc_by_family",
    }
    stage = " ".join(" ".join(c) for c in rep.analysis_stage())
    for bundle in rep._bundle_names():
        if bundle.startswith("confirmatory_"):
            assert "evaluate_confirmatory" in stage
        else:
            assert produced[bundle] in stage, bundle


def test_raw_stage_never_targets_raw_data() -> None:
    for cmd in rep.raw_stage():
        assert not any(a.startswith("data/raw") for a in cmd)
