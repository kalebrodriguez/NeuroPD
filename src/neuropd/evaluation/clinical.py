"""Rank-based partial correlation for clinical-association analyses (ADR 0017).

Spearman partial correlation of a feature with a clinical score, controlling for
covariates: ranks of all variables are taken, covariate ranks are regressed out of
the feature and score ranks, and the residuals are correlated (Pearson). The
two-sided p-value uses a t distribution with ``n - 2 - k`` degrees of freedom, where
``k`` is the number of covariates.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class PartialCorr:
    r: float
    p: float
    n: int
    lo: float
    hi: float


def _residualize(y: np.ndarray, z: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(y)), z])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return y - design @ coef


def partial_spearman_r(x: np.ndarray, y: np.ndarray, covariates: np.ndarray) -> float:
    """Spearman partial correlation of ``x`` and ``y`` given ``covariates`` (no NaNs)."""
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    rz = np.column_stack([stats.rankdata(c) for c in np.atleast_2d(covariates.T)])
    ex, ey = _residualize(rx, rz), _residualize(ry, rz)
    if ex.std() == 0 or ey.std() == 0:
        return float("nan")
    return float(np.corrcoef(ex, ey)[0, 1])


def partial_spearman(
    x: np.ndarray,
    y: np.ndarray,
    covariates: np.ndarray,
    *,
    n_boot: int = 2000,
    seed: int = 20240517,
) -> PartialCorr:
    """Partial Spearman correlation with t-test p-value and percentile bootstrap CI.

    Rows with a NaN in ``x``, ``y`` or any covariate are dropped first.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(covariates, dtype=float).reshape(len(x), -1)
    keep = np.isfinite(x) & np.isfinite(y) & np.isfinite(z).all(axis=1)
    x, y, z = x[keep], y[keep], z[keep]
    n, k = len(x), z.shape[1]
    r = partial_spearman_r(x, y, z)
    dof = n - 2 - k
    if dof <= 0 or not np.isfinite(r) or abs(r) >= 1:
        p = float("nan")
    else:
        t = r * np.sqrt(dof / (1 - r**2))
        p = float(2 * stats.t.sf(abs(t), dof))
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        boots.append(partial_spearman_r(x[idx], y[idx], z[idx]))
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    return PartialCorr(r=r, p=p, n=n, lo=float(lo), hi=float(hi))


def benjamini_hochberg(pvals: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values (NaNs preserved)."""
    p = np.asarray(pvals, dtype=float)
    out = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    pv = p[ok]
    m = len(pv)
    if m == 0:
        return out
    order = np.argsort(pv)
    ranked = pv[order] * m / np.arange(1, m + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    res = np.empty(m)
    res[order] = np.minimum(adj, 1.0)
    out[ok] = res
    return out
