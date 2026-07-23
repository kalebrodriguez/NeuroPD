"""Quality-control metrics and exclusion accounting (spec Section 10.3).

Participants are excluded only for predeclared quality reasons (too-short
recording, too few clean epochs) — never because their data weakens model
performance. Every exclusion carries a reason string.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QCResult:
    """Quality-control summary for a single recording."""

    dataset: str
    participant_id: str
    group: str
    session: str | None
    duration_s: float
    sfreq_in_hz: float
    n_channels: int
    n_epochs_total: int
    n_epochs_clean: int
    excluded: bool
    reasons: list[str] = field(default_factory=list)

    @property
    def rejection_rate(self) -> float:
        if self.n_epochs_total == 0:
            return 1.0
        return 1.0 - self.n_epochs_clean / self.n_epochs_total

    def as_row(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "participant_id": self.participant_id,
            "group": self.group,
            "session": self.session or "",
            "duration_s": round(self.duration_s, 2),
            "sfreq_in_hz": self.sfreq_in_hz,
            "n_channels": self.n_channels,
            "n_epochs_total": self.n_epochs_total,
            "n_epochs_clean": self.n_epochs_clean,
            "rejection_rate": round(self.rejection_rate, 4),
            "excluded": self.excluded,
            "reasons": "; ".join(self.reasons),
        }


def decide_exclusion(
    *,
    duration_s: float,
    n_epochs_clean: int,
    min_recording_duration_s: float,
    min_clean_epochs: int,
) -> tuple[bool, list[str]]:
    """Return ``(excluded, reasons)`` from predeclared QC thresholds."""
    reasons: list[str] = []
    if duration_s < min_recording_duration_s:
        reasons.append(
            f"recording_duration {duration_s:.1f}s < min {min_recording_duration_s:.0f}s"
        )
    if n_epochs_clean < min_clean_epochs:
        reasons.append(f"clean_epochs {n_epochs_clean} < min {min_clean_epochs}")
    return (len(reasons) > 0, reasons)


def qc_table(results: Sequence[QCResult]) -> list[dict[str, Any]]:
    """Convert QC results to a list of table rows."""
    return [r.as_row() for r in results]
