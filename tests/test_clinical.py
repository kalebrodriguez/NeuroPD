"""Partial Spearman correlation and BH-FDR (ADR 0017), offline."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from neuropd.evaluation.clinical import benjamini_hochberg, partial_spearman, partial_spearman_r


def test_partial_removes_confounding_by_age(rng) -> None:
    age = rng.normal(65, 8, 400)
    x = age + rng.normal(0, 3, 400)  # both driven by age only
    y = -age + rng.normal(0, 3, 400)
    raw = stats.spearmanr(x, y).statistic
    assert raw < -0.7
    assert abs(partial_spearman_r(x, y, age[:, None])) < 0.12


def test_partial_recovers_true_association(rng) -> None:
    age = rng.normal(65, 8, 300)
    x = rng.normal(0, 1, 300)
    y = 0.6 * x + 0.05 * age + rng.normal(0, 0.8, 300)
    res = partial_spearman(x, y, age[:, None], n_boot=200)
    assert res.r > 0.4 and res.p < 1e-6 and res.lo < res.r < res.hi
    assert res.n == 300


def test_nan_rows_dropped(rng) -> None:
    x = rng.normal(0, 1, 50)
    y = x + rng.normal(0, 1, 50)
    age = rng.normal(0, 1, 50)
    y[:5] = np.nan
    assert partial_spearman(x, y, age[:, None], n_boot=50).n == 45


def test_constant_covariate_reduces_to_plain_spearman() -> None:
    # With an uninformative (constant) covariate the partial r equals Spearman's rho.
    x = np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=float)
    y = np.array([2, 1, 4, 3, 6, 5, 8, 7], dtype=float)
    z = np.ones(8)
    assert partial_spearman_r(x, y, z[:, None]) == pytest.approx(stats.spearmanr(x, y).statistic)


def test_benjamini_hochberg_matches_known_values() -> None:
    p = np.array([0.01, 0.04, 0.03, 0.005, np.nan])
    adj = benjamini_hochberg(p)
    np.testing.assert_allclose(adj[:4], [0.02, 0.04, 0.04, 0.02])
    assert np.isnan(adj[4])
