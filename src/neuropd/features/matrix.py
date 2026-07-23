"""Participant feature-matrix assembly (spec Sections 6.3, 12.4, 18.1).

Builds the one-row-per-participant table that models consume. Identifier and
label columns (``participant_id``, ``dataset``, ``group``) are kept as an explicit
metadata block, physically separate from the numeric feature columns, so that no
identifier or label can leak into the feature matrix. ``feature_columns`` returns
exactly the modelling columns and is the single source of truth used by both the
modelling pipelines and the leakage tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

# Non-feature columns. Everything else in the assembled frame is a feature.
METADATA_COLUMNS: tuple[str, ...] = (
    "participant_id",
    "dataset",
    "group",
    "n_sessions",
    "n_epochs",
)


@dataclass
class ParticipantRecord:
    """One participant's metadata plus assembled feature values."""

    participant_id: str
    dataset: str
    group: str
    n_sessions: int
    n_epochs: int
    features: dict[str, float] = field(default_factory=dict)


def build_feature_frame(records: list[ParticipantRecord]) -> pd.DataFrame:
    """Assemble participant records into a validated one-row-per-participant frame.

    Raises ``ValueError`` on duplicate participant ids (each participant is one
    row; sessions are pooled upstream — Section 6.1) or inconsistent feature keys.
    """
    if not records:
        raise ValueError("no participant records to assemble")
    ids = [r.participant_id for r in records]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"duplicate participant_id(s) in feature matrix: {dupes}")
    feature_keys = list(records[0].features.keys())
    key_set = set(feature_keys)
    rows = []
    for r in records:
        if set(r.features) != key_set:
            missing = key_set - set(r.features)
            extra = set(r.features) - key_set
            raise ValueError(
                f"{r.participant_id} has inconsistent feature keys "
                f"(missing={sorted(missing)}, extra={sorted(extra)})"
            )
        row = {
            "participant_id": r.participant_id,
            "dataset": r.dataset,
            "group": r.group,
            "n_sessions": r.n_sessions,
            "n_epochs": r.n_epochs,
        }
        row.update({k: r.features[k] for k in feature_keys})
        rows.append(row)
    frame = pd.DataFrame(rows, columns=[*METADATA_COLUMNS, *feature_keys])
    return frame


def feature_columns(frame: pd.DataFrame) -> list[str]:
    """Return only the numeric feature columns (everything but metadata)."""
    return [c for c in frame.columns if c not in METADATA_COLUMNS]
