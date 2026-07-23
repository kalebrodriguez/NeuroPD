"""Leakage tests (spec Section 6.3 / Section 18.1).

The feature matrix must never contain a participant identifier or group label as a
feature column, and each participant must appear exactly once (sessions pooled
upstream, Section 6.1). The scaler-within-training-pipeline test lands in
Milestone 4 with the modelling pipeline.
"""

from __future__ import annotations

import numpy as np
import pytest

from neuropd.config import load_feature_config
from neuropd.features import aggregate as agg
from neuropd.features.matrix import (
    METADATA_COLUMNS,
    ParticipantRecord,
    build_feature_frame,
    feature_columns,
)

SFREQ = 250.0


def _record(pid: str, group: str, rng) -> ParticipantRecord:
    ch_names = ["Fp1", "F3", "C3", "P3", "O1"]
    cfg = load_feature_config()
    data = rng.standard_normal((8, len(ch_names), int(2 * SFREQ))) * 1e-6
    feats = agg.participant_feature_row(data, SFREQ, ch_names, cfg)
    return ParticipantRecord(pid, "dsX", group, n_sessions=1, n_epochs=8, features=feats)


def test_no_identifier_or_label_in_feature_matrix(rng) -> None:
    frame = build_feature_frame([_record("sub-01", "HC", rng), _record("sub-02", "PD", rng)])
    cols = feature_columns(frame)
    for forbidden in ("participant_id", "dataset", "group", "n_sessions", "n_epochs"):
        assert forbidden not in cols
    # No feature column name encodes an identifier or label token.
    for c in cols:
        assert "sub-" not in c
        assert not any(c == m for m in METADATA_COLUMNS)


def test_feature_columns_are_numeric(rng) -> None:
    frame = build_feature_frame([_record("sub-01", "HC", rng), _record("sub-02", "PD", rng)])
    feats = frame[feature_columns(frame)]
    assert all(np.issubdtype(dt, np.number) for dt in feats.dtypes)


def test_duplicate_participant_rejected(rng) -> None:
    with pytest.raises(ValueError, match="duplicate participant_id"):
        build_feature_frame([_record("sub-01", "HC", rng), _record("sub-01", "PD", rng)])


@pytest.mark.skip(reason="Scaler-within-training-pipeline test lands in Milestone 4.")
def test_scaler_fitted_within_training_pipeline() -> None: ...
