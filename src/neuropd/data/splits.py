"""Participant-aware data splitting and isolation guardrails.

Participant isolation is the single most important scientific safeguard in this
project (spec Section 6.1). EEG recordings are divided into many epochs, but
epochs from one participant are *not* independent samples. Any leakage of a
participant across the train/test boundary inflates performance and invalidates
the study.

This module provides a small, well-tested guardrail used throughout the codebase
and enforced by the test suite. Full group-aware cross-validation splitters are
implemented in the internal-modelling milestone; this function is the invariant
they must satisfy.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping


class ParticipantLeakageError(AssertionError):
    """Raised when a participant appears in more than one data partition."""


def find_overlapping_participants(splits: Mapping[str, Iterable[str]]) -> dict[str, list[str]]:
    """Return participants that appear in more than one split.

    Parameters
    ----------
    splits:
        Mapping from split name (e.g. ``"train"``, ``"test"``) to an iterable of
        participant identifiers assigned to that split.

    Returns
    -------
    dict
        Mapping from participant identifier to the sorted list of split names it
        appears in, restricted to participants that appear in two or more splits.
        An empty dict means the partition is disjoint.
    """
    seen: dict[str, set[str]] = {}
    for split_name, participants in splits.items():
        for pid in participants:
            seen.setdefault(pid, set()).add(split_name)
    return {pid: sorted(names) for pid, names in seen.items() if len(names) > 1}


def assert_participants_disjoint(splits: Mapping[str, Iterable[str]]) -> None:
    """Assert that no participant appears in more than one split.

    Parameters
    ----------
    splits:
        Mapping from split name to participant identifiers.

    Raises
    ------
    ParticipantLeakageError
        If any participant appears in two or more splits, listing the offenders.
    """
    overlaps = find_overlapping_participants(splits)
    if overlaps:
        detail = ", ".join(f"{pid} in {names}" for pid, names in sorted(overlaps.items()))
        raise ParticipantLeakageError(f"Participant leakage detected across splits: {detail}")
