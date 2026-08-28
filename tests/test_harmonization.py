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
