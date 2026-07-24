"""Explainability tests (spec Section 15)."""

from __future__ import annotations

import numpy as np
import pytest

from neuropd.modeling.explainability import (
    cross_dataset_agreement,
    logreg_coefficient_importance,
    region_frequency_importance,
)

FEATURES = [
    "rel_power_alpha__occipital__median",
    "rel_power_alpha__occipital__iqr",
    "paf__central__median",
]


def _grouped_data(rng, n=60):
    y = np.array([0, 1] * (n // 2))
    x = rng.standard_normal((n, 3))
    x[:, 0] += 3.0 * y  # feature 0 strongly separates the classes
    groups = np.array([f"sub-{i:02d}" for i in range(n)])
    return x, y, groups


def test_informative_feature_ranks_first_and_is_stable() -> None:
    rng = np.random.default_rng(0)
    x, y, groups = _grouped_data(rng)
    imp = logreg_coefficient_importance(x, y, groups, FEATURES, n_splits=5, n_repeats=3, seed=0)
    top = imp.top_k(1)[0]
    assert top[0] == "rel_power_alpha__occipital__median"
    assert top[3] == pytest.approx(1.0)  # sign consistent across all folds
    assert len(imp.mean_coef) == 3


def test_region_frequency_aggregation() -> None:
    rng = np.random.default_rng(1)
    x, y, groups = _grouped_data(rng)
    imp = logreg_coefficient_importance(x, y, groups, FEATURES, n_splits=5, n_repeats=2, seed=0)
    rf = region_frequency_importance(imp)
    assert set(rf) == {"rel_power_alpha", "paf"}
    assert set(rf["rel_power_alpha"]) == {"occipital"}
    assert set(rf["paf"]) == {"central"}


def test_cross_dataset_agreement_identity_and_mismatch() -> None:
    rng = np.random.default_rng(2)
    x, y, groups = _grouped_data(rng)
    imp = logreg_coefficient_importance(x, y, groups, FEATURES, n_splits=5, n_repeats=2, seed=0)
    assert cross_dataset_agreement(imp, imp) == pytest.approx(1.0)
    imp2 = logreg_coefficient_importance(
        x, y, groups, ["a", "b", "c"], n_splits=5, n_repeats=2, seed=0
    )
    with pytest.raises(ValueError, match="identical feature names"):
        cross_dataset_agreement(imp, imp2)
