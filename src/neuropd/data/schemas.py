"""Data-validation schemas (scaffold).

Explicit schemas/assertions for participant identifiers, group labels, dataset
IDs, session IDs, sampling frequency, channel lists, feature names, missing
values, and units (spec Section 18.3). Concrete Pydantic/pandera-style schemas
are added once the real column names and value ranges are established during the
dataset audit; they must reflect inspected data, not assumptions.
"""

from __future__ import annotations

# Canonical group labels used across the project. Kept minimal and explicit so
# that any unexpected label fails loudly downstream.
GROUP_LABELS: tuple[str, str] = ("HC", "PD")
