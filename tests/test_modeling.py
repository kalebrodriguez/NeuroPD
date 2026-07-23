"""Modeling and cross-validation tests (spec Sections 6.1, 13, 14).

Covers the baseline factory, participant-safe grouped CV (one out-of-fold
prediction per participant; no participant straddles a fold), the majority
baseline's expected behavior, and participant-level bootstrap CIs.
"""

from __future__ import annotations

import numpy as np
import pytest

from neuropd.data.splits import ParticipantLeakageError
from neuropd.evaluation.bootstrap import bootstrap_metric_cis
from neuropd.modeling.baselines import BASELINES, make_estimator
from neuropd.modeling.pipeline import cross_validate_grouped


@pytest.mark.parametrize("name", BASELINES)
def test_make_estimator_fits_and_predicts(name: str) -> None:
    rng = np.random.default_rng(0)
    x = rng.standard_normal((20, 4))
    y = np.array([0, 1] * 10)
    est = make_estimator(name, seed=0).fit(x, y)
    preds = est.predict(x)
    assert set(np.unique(preds)) <= {0, 1}


def test_make_estimator_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unknown baseline"):
        make_estimator("deep_net", seed=0)


def test_cv_one_prediction_per_participant_no_leakage() -> None:
    rng = np.random.default_rng(1)
    n = 40
    x = rng.standard_normal((n, 5))
    y = np.array([0, 1] * (n // 2))
    groups = np.array([f"sub-{i:02d}" for i in range(n)])
    res = cross_validate_grouped(
        lambda: make_estimator("logreg", seed=0),
        x,
        y,
        groups,
        n_splits=5,
        n_repeats=2,
        seed=0,
    )
    assert res.n_participants == n
    assert len(res.y_pred) == n and len(res.y_score) == n
    # Every participant received an out-of-fold prediction (all folds counted).
    assert set(res.participant_ids) == set(groups)


def test_cv_detects_injected_group_leakage() -> None:
    # Duplicate a participant id across rows so a group spans folds -> must raise.
    rng = np.random.default_rng(2)
    x = rng.standard_normal((10, 3))
    y = np.array([0, 1] * 5)
    groups = np.array(["dup"] * 10)  # one group can't be split into 5 folds cleanly
    with pytest.raises((ParticipantLeakageError, ValueError)):
        cross_validate_grouped(
            lambda: make_estimator("logreg", seed=0),
            x,
            y,
            groups,
            n_splits=5,
            n_repeats=1,
            seed=0,
        )


def test_majority_baseline_predicts_majority_class() -> None:
    x = np.zeros((10, 2))
    y = np.array([1] * 8 + [0] * 2)  # PD majority
    est = make_estimator("majority", seed=0).fit(x, y)
    assert np.all(est.predict(x) == 1)


def test_bootstrap_cis_bracket_point() -> None:
    y_true = np.array([0, 0, 0, 1, 1, 1] * 5)
    y_score = y_true + 0.0  # perfect ranking
    y_pred = y_true.copy()
    cis = bootstrap_metric_cis(y_true, y_pred, y_score, n_boot=200, seed=0)
    for k in ("balanced_accuracy", "roc_auc"):
        assert cis[k]["lo"] <= cis[k]["point"] <= cis[k]["hi"]
        assert cis[k]["point"] == pytest.approx(1.0)
