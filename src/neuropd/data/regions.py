"""Scalp-region assignment and channel-set harmonization helpers (pure functions).

Used by the dataset audit and, later, by region-level channel harmonization
(spec Section 11). The region mapping is a documented, provisional convention
based on 10-20 electrode naming; it can be refined via a decision record.

Regions: frontal, central, temporal, parietal, occipital. Assignment uses the
electrode's leading label, checking two-letter prefixes before single-letter ones
so that, e.g., ``FC``/``CP``/``PO`` are not mis-assigned by ``F``/``C``/``P``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

# Ordered (prefix, region): longer/compound prefixes first.
_PREFIX_REGION: tuple[tuple[str, str], ...] = (
    ("Fp", "frontal"),
    ("AF", "frontal"),
    ("FC", "central"),
    ("CP", "parietal"),
    ("FT", "temporal"),
    ("TP", "temporal"),
    ("PO", "occipital"),
    ("F", "frontal"),
    ("C", "central"),
    ("T", "temporal"),
    ("P", "parietal"),
    ("O", "occipital"),
)

REGIONS: tuple[str, ...] = ("frontal", "central", "temporal", "parietal", "occipital")


def assign_region(channel: str) -> str | None:
    """Return the scalp region for a 10-20 electrode name, or ``None`` if unknown.

    Non-scalp channels (e.g. ``EXG*``, ``EOG*``, ``VREF``, ``Status``) return
    ``None`` and should be excluded from region aggregation.
    """
    name = channel.strip()
    upper = name.upper()
    if upper in {"VREF", "STATUS", "TRIG"} or upper.startswith(("EXG", "EOG", "ECG", "EMG")):
        return None
    for prefix, region in _PREFIX_REGION:
        if name.startswith(prefix):
            return region
    return None


def shared_channels(a: Sequence[str], b: Iterable[str]) -> list[str]:
    """Return channels present in both ``a`` and ``b``, preserving ``a``'s order."""
    bset = set(b)
    seen: set[str] = set()
    out: list[str] = []
    for ch in a:
        if ch in bset and ch not in seen:
            out.append(ch)
            seen.add(ch)
    return out


def region_breakdown(channels: Iterable[str]) -> dict[str, list[str]]:
    """Group channels by scalp region (dropping channels with no region)."""
    out: dict[str, list[str]] = {r: [] for r in REGIONS}
    for ch in channels:
        region = assign_region(ch)
        if region is not None:
            out[region].append(ch)
    return out
