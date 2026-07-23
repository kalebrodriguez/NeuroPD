"""Participant-safe cross-validation runner (spec Sections 6.1, 6.3, 13.2).

Runs repeated **stratified, grouped** k-fold cross-validation keyed by participant
so that every fitted transform (imputation, scaling) is learned on the training
fold only, and no participant ever appears in both train and test. Each fold's
partition is checked against the participant-isolation guardrail
(``assert_participants_disjoint``) — the study's primary safeguard.

Out-of-fold predictions are collected per participant and averaged across repeats,
yielding one score/prediction per participant for downstream participant-level
metrics and bootstrap confidence intervals (Section 14.2).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.model_selection import StratifiedGroupKFold

from neuropd.data.splits import assert_participants_disjoint


def positive_scores(estimator: ClassifierMixin, x: np.ndarray) -> np.ndarray:
    """Return a positive-class (PD) score for AUC, from proba or decision function."""
    if hasattr(estimator, "predict_proba"):
        return np.asarray(estimator.predict_proba(x))[:, 1]
    if hasattr(estimator, "decision_function"):
        return np.asarray(estimator.decision_function(x), dtype=float)
    return np.asarray(estimator.predict(x), dtype=float)


@dataclass
class CVResult:
    """Out-of-fold, participant-level cross-validation predictions."""

    y_true: np.ndarray
    y_pred: np.ndarray
    y_score: np.ndarray
    participant_ids: np.ndarray
    n_splits: int
    n_repeats: int
    fold_assignments: list[dict[str, list[str]]]

    @property
    def n_participants(self) -> int:
        return len(self.y_true)


def cross_validate_grouped(
    estimator_factory: Callable[[], ClassifierMixin],
    x: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    *,
    n_splits: int = 5,
    n_repeats: int = 5,
    seed: int = 20240517,
) -> CVResult:
    """Repeated stratified grouped k-fold CV, collecting out-of-fold predictions.

    ``groups`` are participant ids (one row per participant here, but grouping is
    enforced regardless). Scores and hard predictions are averaged/voted across
    repeats to one value per participant.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=int)
    groups = np.asarray(groups)
    n = len(y)
    score_sum = np.zeros(n)
    pred_sum = np.zeros(n)
    counts = np.zeros(n)
    fold_assignments: list[dict[str, list[str]]] = []

    for rep in range(n_repeats):
        cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed + rep)
        for fold, (tr, te) in enumerate(cv.split(x, y, groups)):
            # Primary safeguard: no participant may straddle the split.
            assert_participants_disjoint(
                {"train": groups[tr].tolist(), "test": groups[te].tolist()}
            )
            if rep == 0:
                fold_assignments.append(
                    {"fold": [str(fold)], "test_participants": sorted(groups[te].tolist())}
                )
            est = estimator_factory()
            est.fit(x[tr], y[tr])
            score_sum[te] += positive_scores(est, x[te])
            pred_sum[te] += np.asarray(est.predict(x[te]), dtype=float)
            counts[te] += 1

    y_score = score_sum / counts
    y_pred = (pred_sum / counts >= 0.5).astype(int)
    return CVResult(
        y_true=y,
        y_pred=y_pred,
        y_score=y_score,
        participant_ids=groups,
        n_splits=n_splits,
        n_repeats=n_repeats,
        fold_assignments=fold_assignments,
    )
