"""Feature-family definitions shared by the sensitivity and confirmatory analyses.

A family is a predicate on a participant-matrix column name. Keeping one definition
here guarantees the confirmatory test (ADR 0013) uses exactly the relative-power
family that produced the exploratory result in ADR 0010.
"""

from __future__ import annotations

from collections.abc import Callable

_SLOWING = {"paf", "sef", "theta_alpha_ratio", "delta_alpha_ratio"}
_COMPLEXITY = {
    "spectral_entropy",
    "perm_entropy",
    "hjorth_activity",
    "hjorth_mobility",
    "hjorth_complexity",
}

FAMILIES: dict[str, Callable[[str], bool]] = {
    "relative power": lambda c: c.startswith("rel_power_"),
    "absolute power": lambda c: c.startswith("abs_power_"),
    "log power": lambda c: c.startswith("log_power_"),
    "slowing (paf/sef/ratios)": lambda c: c.split("__")[0] in _SLOWING,
    "complexity": lambda c: c.split("__")[0] in _COMPLEXITY,
}

# The pre-registered primary family (ADR 0013).
PRIMARY_FAMILY = "relative power"


def family_columns(columns: list[str], family: str) -> list[str]:
    """Return the columns of ``family`` in their original order."""
    pred = FAMILIES[family]
    return [c for c in columns if pred(c)]
