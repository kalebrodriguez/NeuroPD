"""Probability calibration diagnostics (spec Section 14.2, 14.4).

A well-discriminating model can still be poorly *calibrated* — its predicted
probabilities may not match observed frequencies, and calibration typically
degrades under external validation. We report the Brier score and a reliability
curve for models that expose probabilities. Models without ``predict_proba``
(e.g. LinearSVC) have no meaningful probability and are skipped.
"""

from __future__ import annotations

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss


def calibration_summary(
    y_true: np.ndarray, y_proba: np.ndarray, *, n_bins: int = 5
) -> dict[str, object]:
    """Brier score and a binned reliability curve for positive-class probabilities.

    Returns ``brier`` (lower is better) and ``curve`` = list of
    ``{"predicted": p, "observed": f}`` points. ``n_bins`` is kept small because
    the external cohort is tiny (30 participants).
    """
    y_true = np.asarray(y_true, dtype=int)
    y_proba = np.asarray(y_proba, dtype=float)
    brier = float(brier_score_loss(y_true, y_proba))
    frac_pos, mean_pred = calibration_curve(y_true, y_proba, n_bins=n_bins, strategy="uniform")
    curve = [
        {"predicted": float(p), "observed": float(f)}
        for p, f in zip(mean_pred, frac_pos, strict=True)
    ]
    return {"brier": brier, "curve": curve}
