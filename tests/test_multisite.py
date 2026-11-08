"""Leave-one-site-out helpers (ADR 0016): leakage and standardization, offline."""

from __future__ import annotations

import numpy as np
import pytest

from neuropd.evaluation.multisite import loso_folds, per_site_zscore, site_ids


def _toy():
    sites = np.array(["a"] * 4 + ["b"] * 3 + ["c"] * 5)
    # Same participant label "sub-001" in two sites must NOT count as overlap.
    pids = np.array(
        [f"sub-00{i}" for i in range(4)]
        + [f"sub-00{i}" for i in range(3)]
        + [f"sub-00{i}" for i in range(5)]
    )
    return sites, pids


def test_each_site_held_out_once_and_never_in_training() -> None:
    sites, pids = _toy()
    folds = list(loso_folds(sites, pids))
    assert [f.held_out for f in folds] == ["a", "b", "c"]
    for f in folds:
        assert set(sites[f.test_idx]) == {f.held_out}
        assert f.held_out not in set(sites[f.train_idx])
        assert len(f.train_idx) + len(f.test_idx) == len(sites)


def test_duplicate_rows_rejected() -> None:
    sites = np.array(["a", "a", "b"])
    pids = np.array(["sub-1", "sub-1", "sub-2"])
    with pytest.raises(ValueError, match="duplicate"):
        list(loso_folds(sites, pids))


def test_single_site_rejected() -> None:
    with pytest.raises(ValueError, match="at least two sites"):
        list(loso_folds(np.array(["a", "a"]), np.array(["1", "2"])))


def test_site_ids_are_prefixed() -> None:
    assert site_ids(np.array(["ds1"]), np.array(["sub-1"])).tolist() == ["ds1:sub-1"]


def test_per_site_zscore_centres_and_scales_each_site(rng) -> None:
    sites = np.array(["a"] * 50 + ["b"] * 40)
    x = rng.normal(0, 1, (90, 3))
    x[sites == "b"] = x[sites == "b"] * 5 + 10
    x[:, 2] = np.where(sites == "a", 7.0, x[:, 2])  # constant within site a
    z = per_site_zscore(x, sites)
    for s in ("a", "b"):
        assert np.allclose(z[sites == s].mean(axis=0), 0, atol=1e-12)
    assert np.allclose(z[sites == "b"].std(axis=0), 1)
    assert np.allclose(z[sites == "a", 2], 0)  # constant column centred, not divided
