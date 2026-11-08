"""Train-safe cross-dataset feature harmonization (spec Sections 11, 27).

The central finding of this project is that the shared EEG feature space is
dominated by **site/acquisition** differences rather than disease (dataset
identity is predicted at AUC ~0.95). This module tests a natural follow-up: if we
remove per-cohort location/scale differences, does the disease signal transfer
better?

Approach — **per-cohort standardization** (a transductive domain-adaptation step):
each cohort's feature matrix is standardized using *its own* feature statistics
(the development cohort with the development stats, the external cohort with the
external stats). Crucially this uses only the external cohort's **unlabeled**
feature distribution — never its labels — so it does not violate the frozen
external-evaluation rule (spec Section 6.2); it is the documented, label-free use
of unlabeled target metadata that Section 6.2 explicitly permits. It is applied
outside the model so the model's own (train-fitted) scaler sees already-aligned
inputs.

This differs from the model's internal ``StandardScaler`` (fit on train, applied
to test with *train* statistics), which cannot correct a site shift because it
leaves the test distribution offset by the between-cohort difference.
"""

from __future__ import annotations

import numpy as np

HARMONIZERS = ("none", "per_cohort_zscore", "per_cohort_robust", "combat", "combat_agesex")


def _standardize(x: np.ndarray, center: np.ndarray, scale: np.ndarray) -> np.ndarray:
    safe = np.where(scale > 0, scale, 1.0)
    return (x - center) / safe


def per_cohort_zscore(x_train: np.ndarray, x_test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Standardize each cohort by its own (nan-aware) mean and std.

    Returns ``(x_train_std, x_test_std)`` with the same shapes. Zero-variance
    columns are left centered (scale 1) to avoid division by zero.
    """
    xtr = np.asarray(x_train, dtype=float)
    xte = np.asarray(x_test, dtype=float)
    tr = _standardize(xtr, np.nanmean(xtr, axis=0), np.nanstd(xtr, axis=0))
    te = _standardize(xte, np.nanmean(xte, axis=0), np.nanstd(xte, axis=0))
    return tr, te


def per_cohort_robust(x_train: np.ndarray, x_test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Standardize each cohort by its own median and IQR (robust to outliers)."""
    xtr = np.asarray(x_train, dtype=float)
    xte = np.asarray(x_test, dtype=float)

    def _center_scale(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        med = np.nanmedian(x, axis=0)
        q75, q25 = np.nanpercentile(x, [75, 25], axis=0)
        return med, (q75 - q25)

    ctr, str_ = _center_scale(xtr)
    cte, ste = _center_scale(xte)
    return _standardize(xtr, ctr, str_), _standardize(xte, cte, ste)


def _fill_covariates(cov: np.ndarray) -> np.ndarray:
    """Fill NaNs per column: median for continuous, mode for 0/1 columns."""
    out = np.asarray(cov, dtype=float).copy()
    for j in range(out.shape[1]):
        col = out[:, j]
        nan = np.isnan(col)
        if not nan.any():
            continue
        finite = col[~nan]
        if finite.size == 0:
            fill = 0.0
        elif set(np.unique(finite)) <= {0.0, 1.0}:
            fill = float(np.round(finite.mean()))
        else:
            fill = float(np.median(finite))
        col[nan] = fill
    return out


def combat(
    x: np.ndarray,
    batch: np.ndarray,
    covariates: np.ndarray | None = None,
    *,
    tol: float = 1e-4,
    max_iter: int = 1000,
) -> np.ndarray:
    """Parametric empirical-Bayes ComBat (Johnson et al. 2007; ADR 0014).

    Parameters
    ----------
    x:
        ``(n_samples, n_features)`` feature matrix (no NaNs).
    batch:
        ``(n_samples,)`` batch labels (here: cohort).
    covariates:
        Optional ``(n_samples, k)`` covariates whose effects are preserved
        (age/sex). NaNs are filled within each batch before fitting.

    Returns the harmonized matrix with the same shape. Each batch's per-feature
    location (gamma) and scale (delta) are shrunk toward priors pooled across
    features, then removed, while the grand mean and covariate effects are kept.
    """
    x = np.asarray(x, dtype=float)
    if np.isnan(x).any():
        raise ValueError("combat requires a complete feature matrix (no NaNs)")
    batch = np.asarray(batch)
    levels = list(dict.fromkeys(batch.tolist()))
    n, _ = x.shape
    onehot = np.column_stack([(batch == lv).astype(float) for lv in levels])
    if covariates is not None:
        cov = np.asarray(covariates, dtype=float).reshape(n, -1).copy()
        for lv in levels:
            idx = batch == lv
            cov[idx] = _fill_covariates(cov[idx])
        cov = cov - cov.mean(axis=0)
        design = np.hstack([onehot, cov])
    else:
        cov = np.zeros((n, 0))
        design = onehot

    coef, *_ = np.linalg.lstsq(design, x, rcond=None)
    n_batch = onehot.sum(axis=0)
    grand_mean = (n_batch / n) @ coef[: len(levels)]
    resid = x - design @ coef
    var_pooled = np.maximum((resid**2).mean(axis=0), 1e-12)
    stand_mean = grand_mean + cov @ coef[len(levels) :]
    z = (x - stand_mean) / np.sqrt(var_pooled)

    out = np.empty_like(z)
    for lv in levels:
        idx = batch == lv
        zb = z[idx]
        nb = zb.shape[0]
        gamma_hat = zb.mean(axis=0)
        delta_hat = np.maximum(zb.var(axis=0, ddof=1), 1e-12)
        gamma_bar, tau2 = gamma_hat.mean(), gamma_hat.var(ddof=1)
        m, s2 = delta_hat.mean(), delta_hat.var(ddof=1)
        a_prior = (2 * s2 + m**2) / s2
        b_prior = (m * s2 + m**3) / s2
        gamma, delta = gamma_hat.copy(), delta_hat.copy()
        for _ in range(max_iter):
            gamma_new = (nb * tau2 * gamma_hat + delta * gamma_bar) / (nb * tau2 + delta)
            ss = ((zb - gamma_new) ** 2).sum(axis=0)
            delta_new = (0.5 * ss + b_prior) / (nb / 2.0 + a_prior - 1.0)
            change = max(
                np.max(np.abs(gamma_new - gamma) / np.maximum(np.abs(gamma), 1e-12)),
                np.max(np.abs(delta_new - delta) / delta),
            )
            gamma, delta = gamma_new, delta_new
            if change < tol:
                break
        out[idx] = (zb - gamma) / np.sqrt(delta)
    return out * np.sqrt(var_pooled) + stand_mean


def combat_pair(
    x_train: np.ndarray,
    x_test: np.ndarray,
    cov_train: np.ndarray | None = None,
    cov_test: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """ComBat over two batches (train cohort, test cohort); unlabeled features only."""
    xtr = np.asarray(x_train, dtype=float)
    xte = np.asarray(x_test, dtype=float)
    x = np.vstack([xtr, xte])
    batch = np.array([0] * len(xtr) + [1] * len(xte))
    cov = None
    if cov_train is not None and cov_test is not None:
        cov = np.vstack([np.asarray(cov_train, float), np.asarray(cov_test, float)])
    h = combat(x, batch, cov)
    return h[: len(xtr)], h[len(xtr) :]


def apply_harmonization(
    x_train: np.ndarray,
    x_test: np.ndarray,
    method: str,
    *,
    cov_train: np.ndarray | None = None,
    cov_test: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Dispatch to a harmonizer by name (``none`` returns inputs unchanged).

    ``combat_agesex`` needs ``cov_train``/``cov_test`` (age, sex) to preserve.
    """
    if method == "combat":
        return combat_pair(x_train, x_test)
    if method == "combat_agesex":
        if cov_train is None or cov_test is None:
            raise ValueError("combat_agesex needs cov_train and cov_test (age, sex)")
        return combat_pair(x_train, x_test, cov_train, cov_test)
    if method == "none":
        return np.asarray(x_train, dtype=float), np.asarray(x_test, dtype=float)
    if method == "per_cohort_zscore":
        return per_cohort_zscore(x_train, x_test)
    if method == "per_cohort_robust":
        return per_cohort_robust(x_train, x_test)
    raise ValueError(f"unknown harmonization method {method!r} (expected {HARMONIZERS})")
