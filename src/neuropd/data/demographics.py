"""Demographic covariates aligned to a participant list (spec Section 6.4).

Age and sex are used for the demographics-only baseline and for confound analysis.
Column names differ across datasets (ds007526 ``sex`` M/F; ds002778 ``gender``),
which this module normalizes. Sex is encoded M=1, F=0; unknown/missing values are
NaN so downstream imputers handle them. This is the single source of truth for
demographics so the baseline and the external transfer use identical encoding.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

import numpy as np

from neuropd.data.audit import read_tsv

# Column holding participant sex per dataset.
_SEX_COLUMN = {"ds007526": "sex", "ds002778": "gender"}

DEMOGRAPHIC_FEATURES: tuple[str, ...] = ("age", "sex_male")


def load_demographics(
    accession: str, participant_ids: list[str], raw_root: Path = Path("data/raw")
) -> np.ndarray:
    """Return an ``(n, 2)`` array of ``[age, sex_male]`` aligned to ``participant_ids``.

    ``sex_male`` is 1.0 for male, 0.0 for female, NaN if unknown. ``age`` is NaN if
    missing or unparseable.
    """
    rows = {r["participant_id"]: r for r in read_tsv(raw_root / accession / "participants.tsv")}
    sex_col = _SEX_COLUMN.get(accession, "sex")
    out = np.full((len(participant_ids), 2), np.nan)
    for i, pid in enumerate(participant_ids):
        row = rows.get(pid, {})
        with contextlib.suppress(ValueError):
            out[i, 0] = float(row.get("age", "nan"))
        sex = str(row.get(sex_col, "")).strip().upper()
        if sex in ("M", "MALE"):
            out[i, 1] = 1.0
        elif sex in ("F", "FEMALE"):
            out[i, 1] = 0.0
    return out
