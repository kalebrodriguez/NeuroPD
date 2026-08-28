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

HARMONIZERS = ("none", "per_cohort_zscore", "per_cohort_robust")


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


def apply_harmonization(
    x_train: np.ndarray, x_test: np.ndarray, method: str
) -> tuple[np.ndarray, np.ndarray]:
    """Dispatch to a harmonizer by name (``none`` returns inputs unchanged)."""
    if method == "none":
        return np.asarray(x_train, dtype=float), np.asarray(x_test, dtype=float)
    if method == "per_cohort_zscore":
        return per_cohort_zscore(x_train, x_test)
    if method == "per_cohort_robust":
        return per_cohort_robust(x_train, x_test)
    raise ValueError(f"unknown harmonization method {method!r} (expected {HARMONIZERS})")
