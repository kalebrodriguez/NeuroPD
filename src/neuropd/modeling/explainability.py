"""Model explainability (spec Section 15).

Interpretable-model explanations used to understand *model behavior*, never to
claim biological causation. For the regularized logistic-regression baseline we
report **standardized coefficients** (the pipeline standardizes features first, so
coefficients are directly comparable in magnitude), their **stability across CV
folds** (mean, std, sign consistency), and a **region x frequency** aggregation of
importance. Cross-dataset agreement is computed by correlating per-feature
importances estimated independently on each cohort.

Predictive importance is not evidence of causality (Section 15).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from neuropd.features.aggregate import NAME_SEP
from neuropd.modeling.baselines import make_estimator


@dataclass
class ImportanceResult:
    """Per-feature standardized-coefficient importance with cross-fold stability."""

    feature_names: list[str]
    mean_coef: np.ndarray  # signed mean standardized coefficient across folds
    std_coef: np.ndarray  # std across folds (stability; lower = more stable)
    sign_consistency: np.ndarray  # fraction of folds sharing the mean sign (0.5-1.0)

    def top_k(self, k: int = 15) -> list[tuple[str, float, float, float]]:
        """Return the ``k`` features with largest |mean coef|, most-important first."""
        order = np.argsort(-np.abs(self.mean_coef))[:k]
        return [
            (
                self.feature_names[i],
                float(self.mean_coef[i]),
                float(self.std_coef[i]),
                float(self.sign_consistency[i]),
            )
            for i in order
        ]


def logreg_coefficient_importance(
    x: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    feature_names: list[str],
    *,
    n_splits: int = 5,
    n_repeats: int = 5,
    seed: int = 20240517,
) -> ImportanceResult:
    """Standardized logistic-regression coefficients aggregated across CV folds."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=int)
    coefs: list[np.ndarray] = []
    for rep in range(n_repeats):
        cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed + rep)
        for tr, _ in cv.split(x, y, groups):
            est = make_estimator("logreg", seed=seed).fit(x[tr], y[tr])
            coefs.append(est.named_steps["clf"].coef_[0])
    stacked = np.vstack(coefs)  # (n_fits, n_features)
    mean_coef = stacked.mean(axis=0)
    std_coef = stacked.std(axis=0)
    mean_sign = np.sign(mean_coef)
    sign_consistency = np.mean(np.sign(stacked) == mean_sign, axis=0)
    return ImportanceResult(feature_names, mean_coef, std_coef, sign_consistency)


def region_frequency_importance(result: ImportanceResult) -> dict[str, dict[str, float]]:
    """Aggregate |mean coef| by base feature and region from ``{base}__{region}__{stat}`` names.

    Returns ``{base_feature: {region: summed_abs_importance}}`` (summed over stats),
    giving a readable region-by-feature importance map (Section 15).
    """
    out: dict[str, dict[str, float]] = {}
    for name, coef in zip(result.feature_names, result.mean_coef, strict=True):
        parts = name.split(NAME_SEP)
        if len(parts) != 3:
            continue
        base, unit, _stat = parts
        out.setdefault(base, {}).setdefault(unit, 0.0)
        out[base][unit] += abs(float(coef))
    return out


def cross_dataset_agreement(a: ImportanceResult, b: ImportanceResult) -> float:
    """Pearson correlation of per-feature mean coefficients across two cohorts.

    High positive correlation means the model relies on similar features in both
    cohorts; low/negative correlation is itself an important finding (Section 15).
    """
    if a.feature_names != b.feature_names:
        raise ValueError("importance results must share identical feature names")
    return float(np.corrcoef(a.mean_coef, b.mean_coef)[0, 1])
