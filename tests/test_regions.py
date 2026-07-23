"""Tests for scalp-region assignment and channel harmonization helpers."""

from __future__ import annotations

from neuropd.data.regions import REGIONS, assign_region, region_breakdown, shared_channels


def test_compound_prefixes_not_misassigned() -> None:
    # Two-letter prefixes must win over single-letter ones.
    assert assign_region("FC1") == "central"
    assert assign_region("CP2") == "parietal"
    assert assign_region("PO3") == "occipital"
    assert assign_region("FT7") == "temporal"
    assert assign_region("AF4") == "frontal"


def test_midline_and_basic_labels() -> None:
    assert assign_region("Fz") == "frontal"
    assert assign_region("Cz") == "central"
    assert assign_region("Pz") == "parietal"
    assert assign_region("Oz") == "occipital"
    assert assign_region("T7") == "temporal"


def test_non_scalp_channels_return_none() -> None:
    for ch in ("EXG1", "EOG2", "VREF", "Status", "ECG1", "EMG3"):
        assert assign_region(ch) is None


def test_shared_channels_preserves_first_order_and_dedupes() -> None:
    a = ["Fz", "Cz", "Pz", "Fz"]
    b = {"Pz", "Fz", "Oz"}
    assert shared_channels(a, b) == ["Fz", "Pz"]


def test_region_breakdown_covers_all_regions() -> None:
    chans = ["Fp1", "FC1", "T7", "P3", "O1", "EXG1"]
    bd = region_breakdown(chans)
    assert set(bd) == set(REGIONS)
    assert bd["frontal"] == ["Fp1"]
    assert bd["central"] == ["FC1"]
    assert bd["temporal"] == ["T7"]
    assert bd["parietal"] == ["P3"]
    assert bd["occipital"] == ["O1"]
