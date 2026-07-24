"""External-transfer and calibration tests (spec Section 14.4)."""

from __future__ import annotations

import numpy as np
import pytest

from neuropd.evaluation.transfer import evaluate_transfer, generalization_gap, transfer_metrics
from neuropd.modeling.baselines import make_estimator
from neuropd.modeling.calibration import calibration_summary


def test_transfer_predicts_on_test_cohort() -> None:
    rng = np.random.default_rng(0)
    # Separable train; the model should transfer to a same-distribution test set.
    x_tr = np.vstack([rng.normal(-2, 0.5, (20, 3)), rng.normal(2, 0.5, (20, 3))])
    y_tr = np.array([0] * 20 + [1] * 20)
    x_te = np.vstack([rng.normal(-2, 0.5, (5, 3)), rng.normal(2, 0.5, (5, 3))])
    y_te = np.array([0] * 5 + [1] * 5)
    ids = np.array([f"t-{i}" for i in range(10)])
    res = evaluate_transfer(
        lambda: make_estimator("logreg", seed=0),
        x_tr,
        y_tr,
        x_te,
        y_te,
        ids,
        train_dataset="A",
        test_dataset="B",
    )
    assert res.train_dataset == "A" and res.test_dataset == "B"
    assert len(res.y_pred) == 10 and len(res.y_score) == 10
    assert list(res.participant_ids) == list(ids)
    assert transfer_metrics(res)["balanced_accuracy"] > 0.9  # separable -> transfers


def test_generalization_gap_signs() -> None:
    internal = {"balanced_accuracy": 0.80, "roc_auc": 0.85}
    external = {"balanced_accuracy": 0.60, "roc_auc": 0.70}
    gap = generalization_gap(internal, external)
    assert gap["balanced_accuracy"] == pytest.approx(0.20)
    assert gap["roc_auc"] == pytest.approx(0.15)


def test_calibration_summary_shape() -> None:
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 100)
    proba = rng.uniform(0, 1, 100)
    summary = calibration_summary(y, proba, n_bins=5)
    assert 0.0 <= summary["brier"] <= 1.0
    assert all({"predicted", "observed"} <= set(pt) for pt in summary["curve"])
