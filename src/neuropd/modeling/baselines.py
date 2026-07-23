"""Baseline models (spec Section 13.1).

The required baselines, in order of complexity: majority-class, demographics-only
logistic regression, regularized EEG-feature logistic regression, linear SVM, and
random forest. Complex models are considered only after these (Section 13.4).

Every model is a scikit-learn ``Pipeline`` so that imputation and scaling are
fitted **inside** training folds only (spec Section 6.3) — never on the full
dataset. Class weighting is ``balanced`` (fitted on the training fold); we never
resample the full dataset (Section 13.3).
"""

from __future__ import annotations

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

# Baseline names in the order they should be reported (Section 13.1). The
# demographics model is trained on age/sex only; the rest on EEG features.
BASELINES: tuple[str, ...] = (
    "majority",
    "demographics",
    "logreg",
    "svm_linear",
    "random_forest",
)
EEG_BASELINES: tuple[str, ...] = ("logreg", "svm_linear", "random_forest")


def make_estimator(name: str, *, seed: int) -> Pipeline:
    """Return a fresh, unfitted pipeline for baseline ``name``.

    Linear models get median imputation + standardization; the random forest gets
    imputation only (trees are scale-invariant). ``majority`` and ``demographics``
    share the generic linear pipeline (``demographics`` is fed only age/sex by the
    caller).
    """
    if name == "majority":
        return Pipeline([("clf", DummyClassifier(strategy="most_frequent"))])

    impute = ("impute", SimpleImputer(strategy="median"))
    scale = ("scale", StandardScaler())

    if name in ("demographics", "logreg"):
        # L2 penalty is the default; specifying it is deprecated in sklearn 1.8.
        clf = LogisticRegression(
            class_weight="balanced",
            max_iter=5000,
            random_state=seed,
        )
        return Pipeline([impute, scale, ("clf", clf)])
    if name == "svm_linear":
        # LinearSVC exposes decision_function (used as the AUC score); it has no
        # predict_proba, which the scoring helper handles.
        clf = LinearSVC(class_weight="balanced", random_state=seed)
        return Pipeline([impute, scale, ("clf", clf)])
    if name == "random_forest":
        clf = RandomForestClassifier(
            n_estimators=400,
            class_weight="balanced",
            random_state=seed,
            n_jobs=-1,
        )
        return Pipeline([impute, ("clf", clf)])

    raise ValueError(f"unknown baseline: {name!r} (expected one of {BASELINES})")
