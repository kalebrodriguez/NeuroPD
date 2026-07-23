"""Tests for participant-isolation guardrails (spec Section 6.1, Section 18.1).

These are high-risk logic: a single leaked participant invalidates the study, so
the guardrail is tested directly here even though full CV splitters arrive in
Milestone 4.
"""

from __future__ import annotations

import pytest

from neuropd.data.splits import (
    ParticipantLeakageError,
    assert_participants_disjoint,
    find_overlapping_participants,
)


def test_disjoint_splits_pass() -> None:
    splits = {"train": ["p1", "p2", "p3"], "test": ["p4", "p5"]}
    assert find_overlapping_participants(splits) == {}
    assert_participants_disjoint(splits)  # must not raise


def test_overlapping_participant_is_detected() -> None:
    splits = {"train": ["p1", "p2"], "test": ["p2", "p3"]}
    overlaps = find_overlapping_participants(splits)
    assert overlaps == {"p2": ["test", "train"]}


def test_assert_raises_on_leakage() -> None:
    splits = {"train": ["p1", "p2"], "test": ["p2"]}
    with pytest.raises(ParticipantLeakageError):
        assert_participants_disjoint(splits)


def test_repeated_sessions_stay_grouped() -> None:
    """A PD participant's ON and OFF sessions must not straddle the split.

    Modelled here at the participant-id level: if both sessions map to the same
    participant id, keeping the participant in one split keeps its sessions
    together (ds002778 has ses-on/ses-off per PD participant).
    """
    # Correct: participant 'pd3' (both sessions) entirely in train.
    good = {"train": ["pd3", "pd5"], "test": ["hc1", "hc2"]}
    assert_participants_disjoint(good)

    # Incorrect: the same participant split across partitions (e.g. sessions leaked).
    bad = {"train": ["pd3"], "test": ["pd3"]}
    with pytest.raises(ParticipantLeakageError):
        assert_participants_disjoint(bad)
