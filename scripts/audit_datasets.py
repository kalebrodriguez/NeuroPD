"""Generate the versioned dataset-audit report (scaffold, Milestone 1).

Computes participant counts, conditions, channels, sampling rates, durations,
confounders, and incompatibilities from the *real* files and writes
``docs/dataset_audit.md`` and ``docs/data_dictionary.md``. Nothing is assumed;
the first task is verifying the ds002778 eye condition (owner decision).
"""

from __future__ import annotations

import sys


def main() -> int:
    sys.stderr.write("audit_datasets is not implemented yet (Milestone 1).\n")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
