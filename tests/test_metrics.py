"""Metrics tests (spec Section 14.1 / Section 18.1).

Metrics are checked against known toy examples: a perfect classifier, a
majority-class classifier on an imbalanced set (where balanced accuracy exposes
what plain accuracy hides), and hand-computed sensitivity/specificity.
"""

from __future__ import annotations

import numpy as np
import pytest

from neuropd.evaluation.metrics import classification_metrics


def test_perfect_classifier() -> None:
    y = np.array([0, 0, 1, 1])
    m = classification_metrics(y, y, y.astype(float))
    assert m["balanced_accuracy"] == pytest.approx(1.0)
    assert m["roc_auc"] == pytest.approx(1.0)
    assert m["sensitivity"] == pytest.approx(1.0)
    assert m["specificity"] == pytest.approx(1.0)
    assert m["f1"] == pytest.approx(1.0)
    assert (m["tn"], m["fp"], m["fn"], m["tp"]) == (2, 0, 0, 2)


def test_majority_class_on_imbalanced_set() -> None:
    # 8 PD, 2 HC; predict all PD. Plain accuracy = 0.8 but balanced accuracy = 0.5.
    y_true = np.array([1] * 8 + [0] * 2)
    y_pred = np.ones_like(y_true)
    m = classification_metrics(y_true, y_pred)
    assert m["balanced_accuracy"] == pytest.approx(0.5)
    assert m["sensitivity"] == pytest.approx(1.0)
    assert m["specificity"] == pytest.approx(0.0)
    assert np.isnan(m["roc_auc"])  # no scores provided


def test_hand_computed_sensitivity_specificity() -> None:
    # tp=3, fn=1 -> sens=0.75 ; tn=4, fp=1 -> spec=0.8
    y_true = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0])
    y_pred = np.array([1, 1, 1, 0, 0, 0, 0, 0, 1])
    m = classification_metrics(y_true, y_pred)
    assert m["sensitivity"] == pytest.approx(0.75)
    assert m["specificity"] == pytest.approx(0.8)
    assert (m["tp"], m["fn"], m["tn"], m["fp"]) == (3, 1, 4, 1)


def test_roc_auc_ranking() -> None:
    y_true = np.array([0, 0, 1, 1])
    good = np.array([0.1, 0.2, 0.8, 0.9])
    m = classification_metrics(y_true, (good > 0.5).astype(int), good)
    assert m["roc_auc"] == pytest.approx(1.0)
    # Reversed scores -> AUC 0.
    m_bad = classification_metrics(y_true, (good > 0.5).astype(int), 1 - good)
    assert m_bad["roc_auc"] == pytest.approx(0.0)
