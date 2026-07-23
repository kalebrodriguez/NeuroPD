"""Participant-level bootstrap confidence intervals (spec Section 14.2).

Confidence intervals are computed by resampling **participants** (not epochs) with
replacement, so the uncertainty reflects the number of independent participants —
the correct unit of analysis (Section 6.1). Each metric's point estimate is on the
observed data; the interval is the percentile CI over bootstrap replicates.
"""

from __future__ import annotations

import numpy as np

from neuropd.evaluation.metrics import classification_metrics


def bootstrap_metric_cis(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: np.ndarray,
    *,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 20240517,
) -> dict[str, dict[str, float]]:
    """Percentile bootstrap CIs (participant resampling) for each metric.

    Returns a mapping ``metric -> {"point", "lo", "hi"}``. A bootstrap replicate
    that happens to contain only one class is skipped for AUC (its AUC is NaN and
    is ignored via ``nanpercentile``).
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    y_score = np.asarray(y_score, dtype=float)
    n = len(y_true)
    rng = np.random.default_rng(seed)

    point = classification_metrics(y_true, y_pred, y_score)
    metric_keys = ["balanced_accuracy", "roc_auc", "sensitivity", "specificity", "f1"]
    replicates: dict[str, list[float]] = {k: [] for k in metric_keys}

    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        m = classification_metrics(y_true[idx], y_pred[idx], y_score[idx])
        for k in metric_keys:
            replicates[k].append(m[k])

    out: dict[str, dict[str, float]] = {}
    lo_q, hi_q = 100 * (alpha / 2), 100 * (1 - alpha / 2)
    for k in metric_keys:
        arr = np.asarray(replicates[k], dtype=float)
        out[k] = {
            "point": float(point[k]),
            "lo": float(np.nanpercentile(arr, lo_q)),
            "hi": float(np.nanpercentile(arr, hi_q)),
        }
    return out
