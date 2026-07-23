"""Feature tests (implemented in Milestone 3).

Placeholders for synthetic-signal checks (spec Section 12.5 / Section 18.1), e.g.
a 10 Hz sine wave dominates the configured alpha band, and aggregation returns
exactly one row per participant.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Features implemented in Milestone 3.")


def test_alpha_sine_dominates_alpha_band() -> None: ...


def test_aggregation_one_row_per_participant() -> None: ...
