"""Tests for train-safe cross-cohort harmonization (ADR 0011)."""

from __future__ import annotations

import numpy as np
import pytest

from neuropd.modeling.harmonization import (
    apply_harmonization,
    per_cohort_robust,
    per_cohort_zscore,
)


def test_none_is_passthrough() -> None:
    a = np.array([[1.0, 2.0], [3.0, 4.0]])
    b = np.array([[10.0, 20.0]])
    xa, xb = apply_harmonization(a, b, "none")
    assert np.array_equal(xa, a)
    assert np.array_equal(xb, b)


def test_per_cohort_zscore_aligns_shifted_scaled_cohorts() -> None:
    rng = np.random.default_rng(0)
    base = rng.normal(0, 1, size=(200, 3))
    # Test cohort is the same signal but shifted +50 and scaled x5 (a pure site effect).
    train = base
    test = base * 5.0 + 50.0
    tr, te = per_cohort_zscore(train, test)
    # After per-cohort z-scoring, both cohorts have ~0 mean / ~1 std per column...
    assert np.allclose(tr.mean(axis=0), 0, atol=1e-6)
    assert np.allclose(te.mean(axis=0), 0, atol=1e-6)
    assert np.allclose(tr.std(axis=0), 1, atol=1e-6)
    assert np.allclose(te.std(axis=0), 1, atol=1e-6)
    # ...and the pure shift/scale difference is removed, so the two align closely.
    assert np.allclose(tr, te, atol=1e-6)


def test_per_cohort_zscore_handles_zero_variance_column() -> None:
    train = np.array([[1.0, 5.0], [1.0, 7.0], [1.0, 9.0]])  # col 0 constant
    test = np.array([[2.0, 1.0], [2.0, 3.0]])
    tr, te = per_cohort_zscore(train, test)
    assert np.isfinite(tr).all() and np.isfinite(te).all()
    assert np.allclose(tr[:, 0], 0.0)  # constant column centered to 0, not inf


def test_per_cohort_robust_shapes_and_finite() -> None:
    rng = np.random.default_rng(1)
    train = rng.normal(3, 2, size=(50, 4))
    test = rng.normal(-1, 0.5, size=(20, 4))
    tr, te = per_cohort_robust(train, test)
    assert tr.shape == train.shape
    assert te.shape == test.shape
    assert np.isfinite(tr).all() and np.isfinite(te).all()


def test_unknown_method_raises() -> None:
    with pytest.raises(ValueError, match="unknown harmonization method"):
        apply_harmonization(np.zeros((2, 2)), np.zeros((2, 2)), "bogus")


def _batchy(seed: int = 0):
    rng = np.random.default_rng(seed)
    n1, n2, p = 80, 50, 12
    age = rng.normal(65, 8, n1 + n2)
    x = rng.normal(0, 1, (n1 + n2, p)) + 0.08 * (age[:, None] - 65)
    batch = np.array([0] * n1 + [1] * n2)
    x[batch == 1] = x[batch == 1] * 2.0 + 3.0  # multiplicative + additive site effect
    return x, batch, age


def test_combat_removes_location_and_scale_batch_effects() -> None:
    from neuropd.modeling.harmonization import combat

    x, batch, _ = _batchy()
    h = combat(x, batch)
    assert h.shape == x.shape
    gap_before = np.abs(x[batch == 0].mean(0) - x[batch == 1].mean(0)).mean()
    gap_after = np.abs(h[batch == 0].mean(0) - h[batch == 1].mean(0)).mean()
    assert gap_after < 0.1 * gap_before
    ratio = h[batch == 1].std(0) / h[batch == 0].std(0)
    assert np.all(np.abs(ratio - 1) < 0.35)


def test_combat_preserves_protected_covariate_effect() -> None:
    """Sites that differ in mean age: protecting age keeps the age-driven gap."""
    from neuropd.modeling.harmonization import combat

    rng = np.random.default_rng(1)
    n1, n2, p = 120, 120, 10
    age = np.concatenate([rng.normal(60, 5, n1), rng.normal(70, 5, n2)])
    batch = np.array([0] * n1 + [1] * n2)
    x = 0.1 * (age[:, None] - 65) + rng.normal(0, 0.5, (n1 + n2, p))
    x[batch == 1] += 3.0  # additive site effect on top of a true 10-year age gap
    true_gap = 0.1 * (age[batch == 1].mean() - age[batch == 0].mean())

    def gap(h: np.ndarray) -> float:
        return float((h[batch == 1].mean(0) - h[batch == 0].mean(0)).mean())

    assert abs(gap(combat(x, batch, age[:, None])) - true_gap) < 0.15
    assert abs(gap(combat(x, batch))) < 0.05  # unprotected: age gap removed with site


def test_combat_rejects_nans_and_combat_agesex_needs_covariates() -> None:
    from neuropd.modeling.harmonization import combat

    x, batch, _ = _batchy()
    x[0, 0] = np.nan
    with pytest.raises(ValueError, match="no NaNs"):
        combat(x, batch)
    with pytest.raises(ValueError, match="needs cov_train"):
        apply_harmonization(np.ones((3, 2)), np.ones((3, 2)), "combat_agesex")


def test_combat_pair_splits_back_in_order() -> None:
    x, batch, age = _batchy(2)
    xa, xb = x[batch == 0], x[batch == 1]
    ha, hb = apply_harmonization(xa, xb, "combat")
    assert ha.shape == xa.shape and hb.shape == xb.shape
    cov_a = np.column_stack([age[batch == 0], np.ones(len(xa))])
    cov_b = np.column_stack([age[batch == 1], np.full(len(xb), np.nan)])  # missing sex
    ha2, hb2 = apply_harmonization(xa, xb, "combat_agesex", cov_train=cov_a, cov_test=cov_b)
    assert np.isfinite(ha2).all() and np.isfinite(hb2).all()


def test_combat_is_scale_equivariant_for_tiny_features() -> None:
    """Absolute band power (~1e-11 V^2) must harmonize like any other feature."""
    from neuropd.modeling.harmonization import combat

    x, batch, age = _batchy(3)
    ref = combat(x, batch, age[:, None])
    tiny = combat(x * 1e-11, batch, age[:, None])
    np.testing.assert_allclose(tiny, ref * 1e-11, rtol=1e-6, atol=0)
