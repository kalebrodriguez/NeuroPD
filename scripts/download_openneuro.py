"""Download OpenNeuro datasets into ``data/raw/`` (scaffold, Milestone 1).

This will fetch ``ds002778`` and ``ds007526`` via an OpenNeuro-supported method
(e.g. openneuro-py / DataLad / AWS S3), verifying sizes and licenses first and
writing checksums. Raw data stay under ``data/raw/`` and are git-ignored. Running
this requires explicit owner approval (spec Section 29.7) and is intentionally
not implemented during Milestone 0.
"""

from __future__ import annotations

import sys


def main() -> int:
    sys.stderr.write(
        "download_openneuro is not implemented yet (Milestone 1, pending owner approval).\n"
    )
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
