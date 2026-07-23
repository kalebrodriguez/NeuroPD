"""Shared pytest fixtures for NeuroPD tests."""

from __future__ import annotations

import numpy as np
import pytest

from neuropd.config import DEFAULT_SEED


@pytest.fixture
def rng() -> np.random.Generator:
    """Seeded NumPy random generator for deterministic tests."""
    return np.random.default_rng(DEFAULT_SEED)
