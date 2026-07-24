"""Evaluation metrics (spec Section 14.1).

Imbalance-robust classification metrics for participant-level PD-vs-HC evaluation.
Accuracy alone is never sufficient (Section 14.1), so the primary summary is
balanced accuracy plus ROC-AUC, sensitivity, specificity, and F1. All metrics are
validated against known toy examples in ``tests/test_metrics.py``.

Convention: the positive class is **PD** (label 1); HC is 0. ``sensitivity`` is
the PD true-positive rate; ``specificity`` is the HC true-negative rate.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)

POSITIVE_LABEL = 1  # PD


def classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: np.ndarray | None = None,
) -> dict[str, float]:
    """Compute imbalance-robust metrics for a binary (HC=0, PD=1) problem.

    Parameters
    ----------
    y_true, y_pred:
        Ground-truth and predicted labels in {0, 1}.
    y_score:
        Optional predicted probability/score for the positive class (PD). Required
        for ROC-AUC; when ``None`` (or only one class present) AUC is ``nan``.

    Returns
    -------
    dict
        ``balanced_accuracy``, ``roc_auc``, ``sensitivity``, ``specificity``,
        ``f1``, and the confusion counts ``tn``, ``fp``, ``fn``, ``tp``.
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    specificity = tn / (tn + fp) if (tn + fp) > 0 else float("nan")

    if y_score is not None and len(np.unique(y_true)) == 2:
        roc_auc = float(roc_auc_score(y_true, np.asarray(y_score, dtype=float)))
    else:
        roc_auc = float("nan")

    return {
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "roc_auc": roc_auc,
        "sensitivity": float(sensitivity),
        "specificity": float(specificity),
        "f1": float(f1_score(y_true, y_pred, pos_label=POSITIVE_LABEL, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }
