"""Provenance capture for reproducible NeuroPD runs.

Every analysis output must be traceable to the software and platform that
produced it (spec Section 7 and Section 24). This module collects a compact,
JSON-serialisable record of:

* NeuroPD version and (when available) the Git commit,
* Python and platform details,
* versions of key scientific dependencies,
* the active random seed and a UTC timestamp.

The record is intentionally free of any dataset content or identifiers so it can
be committed alongside results without privacy concerns.
"""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from neuropd import __version__
from neuropd.config import DEFAULT_SEED

# Dependencies whose exact versions materially affect numerical results.
_TRACKED_PACKAGES = (
    "mne",
    "mne-bids",
    "numpy",
    "pandas",
    "scipy",
    "scikit-learn",
    "statsmodels",
)


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for pkg in _TRACKED_PACKAGES:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = "not-installed"
    return versions


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    commit = out.stdout.strip()
    return commit or None


def collect_provenance(seed: int = DEFAULT_SEED) -> dict[str, Any]:
    """Return a JSON-serialisable provenance record for the current run.

    Parameters
    ----------
    seed:
        The active random seed for the run being recorded.
    """
    return {
        "neuropd_version": __version__,
        "git_commit": _git_commit(),
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "seed": seed,
        "packages": _package_versions(),
    }


def write_provenance(path: str | Path, seed: int = DEFAULT_SEED) -> Path:
    """Write the provenance record to ``path`` as indented JSON.

    Parameters
    ----------
    path:
        Destination file path. Parent directories are created if needed.
    seed:
        The active random seed for the run being recorded.

    Returns
    -------
    pathlib.Path
        The path that was written.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(collect_provenance(seed=seed), indent=2) + "\n", encoding="utf-8")
    return p
