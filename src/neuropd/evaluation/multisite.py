"""Leave-one-site-out (LOSO) helpers for multi-site training (ADR 0016).

A *site* is a cohort. Each LOSO fold trains on every other site pooled and tests
once on the held-out site. Participant identifiers are prefixed with their site
so that ids are unique across cohorts, and every fold is checked for participant
disjointness (spec Section 6.1).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np

from neuropd.data.splits import assert_participants_disjoint


@dataclass(frozen=True)
class LosoFold:
    """Row indices of one leave-one-site-out fold."""

    held_out: str
    train_idx: np.ndarray
    test_idx: np.ndarray


def site_ids(sites: np.ndarray, participant_ids: np.ndarray) -> np.ndarray:
    """Return ``"<site>:<participant>"`` identifiers (unique across cohorts)."""
    return np.array([f"{s}:{p}" for s, p in zip(sites, participant_ids, strict=True)])


def loso_folds(sites: np.ndarray, participant_ids: np.ndarray) -> Iterator[LosoFold]:
    """Yield one fold per site, in first-appearance order, with leakage checks."""
    sites = np.asarray(sites)
    uid = site_ids(sites, np.asarray(participant_ids))
    if len(set(uid.tolist())) != len(uid):
        raise ValueError("duplicate site:participant rows; aggregate to one row each first")
    for site in dict.fromkeys(sites.tolist()):
        test = np.flatnonzero(sites == site)
        train = np.flatnonzero(sites != site)
        if train.size == 0:
            raise ValueError("leave-one-site-out needs at least two sites")
        assert_participants_disjoint({"train": uid[train].tolist(), "test": uid[test].tolist()})
        yield LosoFold(held_out=str(site), train_idx=train, test_idx=test)


def per_site_zscore(x: np.ndarray, sites: np.ndarray) -> np.ndarray:
    """Standardize each site's rows by that site's own (unlabeled) mean and SD.

    Zero-variance columns within a site are centred only. NaNs are ignored when
    computing statistics and preserved in the output.
    """
    x = np.asarray(x, dtype=float)
    out = np.empty_like(x)
    for site in np.unique(sites):
        idx = sites == site
        mu = np.nanmean(x[idx], axis=0)
        sd = np.nanstd(x[idx], axis=0)
        out[idx] = (x[idx] - mu) / np.where(sd > 0, sd, 1.0)
    return out
