"""Cross-dataset transfer evaluation (spec Section 14.4).

Frozen external evaluation: fit a model on the entire development cohort and
evaluate it once on the entire, held-out external cohort. The external cohort is
never used for supervised tuning (Section 6.2); the pipeline and analysis plan are
frozen before this runs. Bidirectional transfer (A->B and B->A) is treated as two
separate experiments.

The generalization gap is the drop from internal (cross-validated) performance on
the development cohort to external performance on the other cohort.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from sklearn.base import ClassifierMixin

from neuropd.evaluation.metrics import classification_metrics
from neuropd.modeling.pipeline import positive_scores


@dataclass
class TransferResult:
    """Out-of-cohort predictions from a model trained on the development cohort."""

    y_true: np.ndarray
    y_pred: np.ndarray
    y_score: np.ndarray
    participant_ids: np.ndarray
    train_dataset: str
    test_dataset: str


def evaluate_transfer(
    estimator_factory: Callable[[], ClassifierMixin],
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
    test_ids: np.ndarray,
    *,
    train_dataset: str,
    test_dataset: str,
) -> TransferResult:
    """Fit on the full development cohort; predict once on the full external cohort."""
    est = estimator_factory()
    est.fit(np.asarray(x_train, dtype=float), np.asarray(y_train, dtype=int))
    x_test = np.asarray(x_test, dtype=float)
    return TransferResult(
        y_true=np.asarray(y_test, dtype=int),
        y_pred=np.asarray(est.predict(x_test), dtype=int),
        y_score=positive_scores(est, x_test),
        participant_ids=np.asarray(test_ids),
        train_dataset=train_dataset,
        test_dataset=test_dataset,
    )


def generalization_gap(internal: dict[str, float], external: dict[str, float]) -> dict[str, float]:
    """Per-metric drop ``internal - external`` (positive = worse on the external cohort)."""
    return {k: float(internal[k] - external[k]) for k in internal if k in external}


def transfer_metrics(result: TransferResult) -> dict[str, float]:
    """Convenience: classification metrics for a transfer result."""
    return classification_metrics(result.y_true, result.y_pred, result.y_score)
