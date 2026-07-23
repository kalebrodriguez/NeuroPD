"""Pure functions for the dataset audit (spec Section 5.1).

These operate on already-parsed data structures / files on disk so they can be
unit-tested offline with no network access. Orchestration and report writing
live in ``scripts/audit_datasets.py``.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from neuropd.data.regions import assign_region

MISSING = {"", "n/a", "na", "nan", "none", None}


def read_tsv(path: str | Path) -> list[dict[str, str]]:
    """Read a TSV file into a list of row dicts (BOM- and whitespace-tolerant)."""
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    if not lines:
        return []
    header = lines[0].split("\t")
    rows: list[dict[str, str]] = []
    for ln in lines[1:]:
        cells = ln.split("\t")
        cells += [""] * (len(header) - len(cells))
        rows.append(dict(zip(header, cells, strict=False)))
    return rows


def read_json(path: str | Path) -> dict[str, Any]:
    """Read a JSON file into a dict."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in {m for m in MISSING if m is not None}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def numeric_stats(values: Iterable[Any]) -> dict[str, Any]:
    """Summary stats over numeric values, ignoring missing entries."""
    nums = [f for f in (_to_float(v) for v in values) if f is not None]
    raw = list(values)
    out: dict[str, Any] = {"n": len(nums), "missing": len(raw) - len(nums)}
    if nums:
        out["mean"] = round(statistics.fmean(nums), 3)
        out["min"] = min(nums)
        out["max"] = max(nums)
        out["sd"] = round(statistics.pstdev(nums), 3) if len(nums) > 1 else 0.0
    return out


def participant_group(participant_id: str, explicit_group: str | None = None) -> str | None:
    """Return ``"HC"``/``"PD"`` from an explicit group or the id prefix.

    Never guesses beyond the documented conventions: an explicit ``group`` value
    wins; otherwise ``sub-hc*`` -> HC and ``sub-pd*`` -> PD (ds002778). Anything
    else returns ``None`` and must be handled/failed loudly by the caller.
    """
    if explicit_group is not None:
        g = explicit_group.strip().upper()
        if g in {"HC", "PD"}:
            return g
    pid = participant_id.strip().lower().removeprefix("sub-")
    if pid.startswith("hc"):
        return "HC"
    if pid.startswith("pd"):
        return "PD"
    return None


def summarize_demographics(
    rows: Sequence[dict[str, str]],
    *,
    id_col: str = "participant_id",
    group_col: str | None = None,
    age_col: str | None = "age",
    sex_col: str | None = None,
) -> dict[str, Any]:
    """Compute per-group participant counts and age/sex breakdowns."""
    groups: dict[str, list[dict[str, str]]] = {"HC": [], "PD": [], "UNKNOWN": []}
    for r in rows:
        g = participant_group(r.get(id_col, ""), r.get(group_col) if group_col else None)
        groups[g or "UNKNOWN"].append(r)

    summary: dict[str, Any] = {"total": len(rows)}
    for g, grows in groups.items():
        if not grows and g == "UNKNOWN":
            continue
        entry: dict[str, Any] = {"n": len(grows)}
        if age_col:
            entry["age"] = numeric_stats([r.get(age_col, "") for r in grows])
        if sex_col:
            sexes: dict[str, int] = {}
            for r in grows:
                s = (r.get(sex_col, "") or "").strip().upper() or "n/a"
                sexes[s] = sexes.get(s, 0) + 1
            entry["sex"] = sexes
        summary[g] = entry
    return summary


def scalp_channels(channel_rows: Sequence[dict[str, str]]) -> list[str]:
    """Return scalp EEG channel names (region-mappable) from a channels.tsv.

    Drops non-scalp channels (EOG/EXG/VREF/trigger) via region assignment.
    """
    out: list[str] = []
    for r in channel_rows:
        name = (r.get("name") or "").strip()
        if not name:
            continue
        if assign_region(name) is not None:
            out.append(name)
    return out


def aggregate_recording_params(eeg_jsons: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate key acquisition parameters across recordings, checking uniformity."""

    def _unique(key: str) -> list[Any]:
        vals = {json.dumps(j.get(key)) for j in eeg_jsons}
        return sorted(json.loads(v) for v in vals)

    def _counts(key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for j in eeg_jsons:
            k = json.dumps(j.get(key))
            out[k] = out.get(k, 0) + 1
        return out

    durations = [j.get("RecordingDuration") for j in eeg_jsons]
    return {
        "n_recordings": len(eeg_jsons),
        "sampling_frequency_hz": _unique("SamplingFrequency"),
        "power_line_frequency_hz": _unique("PowerLineFrequency"),
        "power_line_frequency_counts": _counts("PowerLineFrequency"),
        "eeg_channel_count": _unique("EEGChannelCount"),
        "eeg_reference": _unique("EEGReference"),
        "recording_duration_s": numeric_stats(durations),
    }
