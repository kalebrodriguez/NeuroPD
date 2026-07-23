"""Minimal OpenNeuro client for **metadata-only** retrieval.

This module fetches small BIDS sidecar/metadata files (``*.json``, ``*.tsv``)
from OpenNeuro snapshots via the public GraphQL API. It deliberately **never**
downloads the large binary recordings (``*.set``, ``*.fdt``, ``*.bdf``,
``*.edf``, ``*.fif``, ...); downloading full datasets is a separate,
approval-gated step (spec Section 29.7).

Only the Python standard library is used so that the dataset audit has no extra
runtime dependency.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from neuropd.logging import get_logger

GRAPHQL_URL = "https://openneuro.org/crn/graphql"
_LOG = get_logger("neuropd.openneuro")

# Binary recording formats that must never be downloaded by this metadata client.
BINARY_SUFFIXES: frozenset[str] = frozenset(
    {".set", ".fdt", ".bdf", ".edf", ".fif", ".vhdr", ".eeg", ".vmrk", ".gz", ".nii"}
)
# Small metadata files that are safe to retrieve.
METADATA_SUFFIXES: frozenset[str] = frozenset({".json", ".tsv"})


@dataclass(frozen=True)
class DatasetRef:
    """A pinned OpenNeuro dataset snapshot."""

    accession: str
    tag: str
    role: str


# Owner-approved cohorts (see docs/decisions/0001-cohort-roles.md).
DATASETS: dict[str, DatasetRef] = {
    "ds007526": DatasetRef("ds007526", "1.0.2", "development"),
    "ds002778": DatasetRef("ds002778", "1.0.5", "external_validation"),
}


@dataclass
class FileNode:
    """A node in an OpenNeuro snapshot file tree."""

    filename: str
    directory: bool
    id: str | None = None
    size: int | None = None
    urls: list[str] = field(default_factory=list)


def _graphql(query: str, *, retries: int = 4, timeout: float = 30.0) -> dict:
    """POST a GraphQL query, returning the ``data`` payload.

    Retries with exponential backoff on transient network/HTTP errors.
    """
    body = json.dumps({"query": query}).encode("utf-8")
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                GRAPHQL_URL, data=body, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # Transient network errors (incl. RemoteDisconnected) -> retry.
            last_err = exc
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
            continue
        if "errors" in payload:
            # A GraphQL-level error is not transient; fail immediately.
            raise RuntimeError(f"GraphQL error: {payload['errors']}")
        return payload["data"]
    raise RuntimeError(f"GraphQL request failed after {retries} attempts: {last_err}")


def _files_query(dataset_id: str, tag: str, tree: str | None) -> str:
    tree_arg = f'(tree: "{tree}")' if tree else ""
    return (
        f'query {{ snapshot(datasetId: "{dataset_id}", tag: "{tag}") '
        f"{{ files{tree_arg} {{ id filename directory size urls }} }} }}"
    )


def list_tree(dataset_id: str, tag: str, tree: str | None = None) -> list[FileNode]:
    """List one level of a snapshot file tree (root when ``tree`` is ``None``)."""
    data = _graphql(_files_query(dataset_id, tag, tree))
    nodes = data["snapshot"]["files"]
    return [
        FileNode(
            filename=n["filename"],
            directory=bool(n.get("directory")),
            id=n.get("id"),
            size=n.get("size"),
            urls=list(n.get("urls") or []),
        )
        for n in nodes
    ]


def walk_files(
    dataset_id: str,
    tag: str,
    *,
    dir_filter: Callable[[str], bool] | None = None,
) -> Iterator[tuple[str, FileNode]]:
    """Recursively yield ``(relative_path, file_node)`` for every file in a snapshot.

    Parameters
    ----------
    dir_filter:
        Optional predicate on a directory's *relative path*; when it returns
        ``False`` the directory is not descended (used to skip, e.g.,
        ``sourcedata`` or non-target tasks to limit API load).
    """

    def _recurse(tree: str | None, prefix: str) -> Iterator[tuple[str, FileNode]]:
        for node in list_tree(dataset_id, tag, tree):
            rel = f"{prefix}{node.filename}"
            if node.directory:
                if dir_filter is not None and not dir_filter(rel):
                    continue
                yield from _recurse(node.id, f"{rel}/")
            else:
                yield rel, node

    yield from _recurse(None, "")


def _download(url: str, dest: Path, *, retries: int = 4, timeout: float = 60.0) -> None:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "neuropd-audit"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = exc
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Download failed for {url}: {last_err}")


def download_metadata(
    dataset_id: str,
    tag: str,
    dest_root: Path,
    *,
    include_suffixes: frozenset[str] = METADATA_SUFFIXES,
    path_filter: Callable[[str], bool] | None = None,
    dir_filter: Callable[[str], bool] | None = None,
    overwrite: bool = False,
) -> list[Path]:
    """Download only small metadata files (``*.json``/``*.tsv``) for a snapshot.

    Binary recording formats are refused even if somehow requested, as a
    defensive guard against accidental full-dataset downloads.

    Returns the list of written paths (mirroring the BIDS layout under
    ``dest_root``).
    """
    written: list[Path] = []
    for rel, node in walk_files(dataset_id, tag, dir_filter=dir_filter):
        suffix = Path(node.filename).suffix.lower()
        if suffix in BINARY_SUFFIXES:
            continue
        if suffix not in include_suffixes:
            continue
        if path_filter is not None and not path_filter(rel):
            continue
        if not node.urls:
            continue
        dest = dest_root / rel
        if dest.exists() and not overwrite:
            written.append(dest)
            continue
        try:
            _download(node.urls[0], dest)
        except RuntimeError as exc:
            # Skip an individual unreachable file rather than aborting the audit;
            # the run is resumable (existing files are skipped on re-run).
            _LOG.warning("Skipping %s: %s", rel, exc)
            continue
        written.append(dest)
    return written


def download_dataset(
    dataset_id: str,
    tag: str,
    dest_root: Path,
    *,
    path_filter: Callable[[str], bool] | None = None,
    dir_filter: Callable[[str], bool] | None = None,
    overwrite: bool = False,
    log_every: int = 25,
) -> list[Path]:
    """Download a full dataset snapshot (including binary recordings) to ``dest_root``.

    Downloading full recordings is approval-gated (spec Section 29.7); this
    function must only be invoked after the project owner approves. It is
    resumable: existing files are skipped unless ``overwrite`` is set. Use
    ``path_filter``/``dir_filter`` to restrict to, e.g., the resting-state task.

    Returns the list of written file paths (mirroring the BIDS layout).
    """
    written: list[Path] = []
    total_bytes = 0
    n = 0
    for rel, node in walk_files(dataset_id, tag, dir_filter=dir_filter):
        if path_filter is not None and not path_filter(rel):
            continue
        if not node.urls:
            continue
        dest = dest_root / rel
        if dest.exists() and not overwrite:
            written.append(dest)
            continue
        try:
            _download(node.urls[0], dest)
        except RuntimeError as exc:
            _LOG.warning("Skipping %s: %s", rel, exc)
            continue
        written.append(dest)
        n += 1
        total_bytes += node.size or dest.stat().st_size
        if n % log_every == 0:
            _LOG.info("  downloaded %d files (%.1f MiB)", n, total_bytes / 1024 / 1024)
    _LOG.info("Downloaded %d new files (%.1f MiB) to %s", n, total_bytes / 1024 / 1024, dest_root)
    return written


def sha256_file(path: Path, *, chunk: int = 1 << 20) -> str:
    """Return the hex SHA-256 of a file, read in chunks."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()
