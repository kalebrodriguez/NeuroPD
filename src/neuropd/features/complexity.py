"""Complexity features (spec Section 12.2).

Time-domain signal-complexity measures computed per channel per epoch. Spectral
entropy (a frequency-domain complexity measure) lives in ``spectral`` and is
combined with these at assembly time. Each function operates on a 1-D signal and
has a synthetic-signal unit test (Section 12.5).

References
----------
Hjorth, B. (1970). EEG analysis based on time domain properties.
    Electroencephalogr. Clin. Neurophysiol. 29(3), 306-310.
Bandt, C. & Pompe, B. (2002). Permutation entropy: a natural complexity measure
    for time series. Phys. Rev. Lett. 88(17), 174102.
"""

from __future__ import annotations

from itertools import permutations
from math import factorial

import numpy as np


def hjorth_parameters(sig: np.ndarray) -> tuple[float, float, float]:
    """Return Hjorth ``(activity, mobility, complexity)`` of a 1-D signal.

    * activity  = variance of the signal (signal power). Units: V**2.
    * mobility  = sqrt(var(dx)/var(x)); proportional to mean frequency (dimensionless).
    * complexity = mobility(dx)/mobility(x); how far the signal departs from a pure
      sine (== 1 for a sinusoid). Dimensionless.

    Returns ``nan`` values for a constant signal (zero variance).
    """
    sig = np.asarray(sig, dtype=float)
    var_zero = np.var(sig)
    if var_zero <= 0:
        return (float(var_zero), float("nan"), float("nan"))
    dx = np.diff(sig)
    var_d1 = np.var(dx)
    mobility = float(np.sqrt(var_d1 / var_zero))
    if var_d1 <= 0:
        return (float(var_zero), mobility, float("nan"))
    ddx = np.diff(dx)
    var_d2 = np.var(ddx)
    mobility_d1 = np.sqrt(var_d2 / var_d1)
    complexity = float(mobility_d1 / mobility) if mobility > 0 else float("nan")
    return (float(var_zero), mobility, complexity)


def permutation_entropy(sig: np.ndarray, order: int = 3, delay: int = 1) -> float:
    """Normalized permutation entropy of a 1-D signal (0..1).

    Counts the relative frequency of each ordinal pattern (the rank order of
    ``order`` samples spaced ``delay`` apart) and returns the Shannon entropy of
    that distribution divided by ``log(order!)``. Regular signals score low;
    noise scores near 1. Returns ``nan`` if the signal is too short.

    Ties are broken by ``argsort``'s stable order, which is standard for the
    Bandt-Pompe estimator on continuous signals where exact ties are rare.
    """
    sig = np.asarray(sig, dtype=float)
    n = len(sig)
    span = delay * (order - 1)
    if n - span < 2:
        return float("nan")
    patterns: dict[tuple[int, ...], int] = {p: 0 for p in permutations(range(order))}
    count = 0
    for i in range(n - span):
        window = sig[i : i + span + 1 : delay]
        pattern = tuple(np.argsort(window))
        patterns[pattern] += 1
        count += 1
    probs = np.array([c for c in patterns.values() if c > 0], dtype=float) / count
    entropy = -np.sum(probs * np.log(probs))
    return float(entropy / np.log(factorial(order)))
