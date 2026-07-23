"""Leakage tests (implemented in Milestone 3/4).

Placeholders (spec Section 18.1): no label or participant identifier enters the
feature matrix; scaling and imputation are fitted only within training pipelines.
The participant-partition invariant is already tested in ``test_splits.py``.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Feature/pipeline leakage tests land in Milestone 3/4.")


def test_no_identifier_in_feature_matrix() -> None: ...


def test_scaler_fitted_within_training_pipeline() -> None: ...
