"""Offline tests for the cohort adapters used by the confirmatory cohorts (ADR 0013).

Covers dataset-specific group spellings, case-insensitive participants.tsv columns,
case-insensitive BIDS task labels and EEGLAB file discovery, using tiny
synthetic BIDS trees (no download).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from neuropd.data.audit import participant_group, row_value
from neuropd.data.demographics import load_demographics
from neuropd.data.loaders import iter_recordings


@pytest.mark.parametrize(
    ("label", "expected"),
    [("PD", "PD"), ("Control", "HC"), ("CTL", "HC"), ("hc", "HC"), ("other", None)],
)
def test_participant_group_control_spellings(label: str, expected: str | None) -> None:
    assert participant_group("sub-001", label) == expected


def test_row_value_is_case_insensitive_with_exact_match_first() -> None:
    assert row_value({"GROUP": "PD"}, "group") == "PD"
    assert row_value({"group": "HC", "GROUP": "PD"}, "group") == "HC"
    assert row_value({"age": "70"}, "sex") is None


def _write_bids(root: Path, rows: list[str], files: list[str]) -> None:
    root.mkdir(parents=True)
    (root / "participants.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    for rel in files:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("", encoding="utf-8")


def test_iter_recordings_matches_task_case(tmp_path: Path) -> None:
    root = tmp_path / "dsX"
    _write_bids(
        root,
        ["participant_id\tGROUP\tAGE\tGENDER", "sub-001\tPD\t70\tM", "sub-002\tControl\t65\tF"],
        [
            "sub-001/eeg/sub-001_task-Rest_eeg.set",
            "sub-001/eeg/sub-001_task-Rest_eeg.fdt",  # EEGLAB data file, not a header
            "sub-002/eeg/sub-002_task-Rest_eeg.set",
            "sub-002/eeg/sub-002_task-walk_eeg.set",  # other task, skipped
        ],
    )
    recs = list(iter_recordings("dsX", tmp_path, task="rest"))
    assert [(r.participant_id, r.group, r.task) for r in recs] == [
        ("sub-001", "PD", "Rest"),
        ("sub-002", "HC", "Rest"),
    ]
    assert all(r.path.suffix == ".set" for r in recs)


def test_load_demographics_uppercase_columns(tmp_path: Path) -> None:
    _write_bids(
        tmp_path / "ds004584",
        ["participant_id\tGROUP\tAGE\tGENDER", "sub-001\tPD\t80\tM", "sub-002\tControl\tn/a\tF"],
        [],
    )
    out = load_demographics("ds004584", ["sub-002", "sub-001", "sub-404"], raw_root=tmp_path)
    assert np.isnan(out[0, 0]) and out[0, 1] == 0.0
    assert out[1].tolist() == [80.0, 1.0]
    assert np.isnan(out[2]).all()
