"""Re-run the NeuroPD analyses and verify them against the committed results.

Runs every analysis script in dependency order, then compares each freshly written
result table (``reports/tables/*.json``) with its committed bundle in
``dashboard/data/``, ignoring generation timestamps. Tracked documents that the
scripts rewrite are compared with ``HEAD`` the same way: a timestamp-only change is
restored, and any other change is reported as a real difference.

Modes:
    --from features   (default) start from the existing feature matrices.
    --from raw        re-preprocess the raw EEG and re-extract every feature matrix
                      first (hours). This rewrites the git-ignored derived data under
                      ``data/processed*``. Raw data are never modified.
    --verify-only     skip all stages; only compare existing tables with the bundles.

The working tree must be clean (no uncommitted tracked changes), so that a change
seen after the run can only come from the run itself. Writes a summary to
``reports/reproduce_summary.md`` (git-ignored) and prints it.

Usage:
    uv run python scripts/reproduce.py                 # make reproduce
    uv run python scripts/reproduce.py --from raw      # make reproduce-raw
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PY = [sys.executable]
DATASETS = ("ds007526", "ds002778", "ds004584", "ds003490")
CONFIRMATORY = ("ds004584", "ds003490")
LENIENT = ("200", "400")  # ADR 0020 artifact thresholds (µV)
TABLES = Path("reports/tables")
BUNDLES = Path("dashboard/data")
SUMMARY = Path("reports/reproduce_summary.md")
_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)?")
_VOLATILE_KEYS = {"generated_utc"}


def _script(name: str, *args: str) -> list[str]:
    return [*PY, f"scripts/{name}.py", *args]


def raw_stage() -> list[list[str]]:
    """Preprocessing and feature extraction from raw EEG (primary + ADR 0020 arms)."""
    cmds = [_script("preprocess", "--dataset", d, "--limit-per-group", "0") for d in DATASETS]
    cmds += [_script("extract_features")]
    cmds += [_script("extract_features", "--exclude-channels", "PO3,PO4")]
    cmds += [
        _script("extract_features", "--spatial", "channel", "--dataset", d) for d in DATASETS[:2]
    ]
    cmds += [_script("extract_aperiodic")]
    for uv in LENIENT:
        root = f"data/processed_qc{uv}"
        cmds += [
            _script(
                "preprocess",
                "--dataset",
                d,
                "--limit-per-group",
                "0",
                "--reject-uv",
                uv,
                "--out-root",
                root,
            )
            for d in DATASETS
        ]
        cmds += [_script("extract_features", "--processed-root", root)]
    return cmds


def analysis_stage() -> list[list[str]]:
    """Every analysis that writes a committed result, in dependency order."""
    cmds = [
        _script("qc_report"),
        _script("train"),
        _script("evaluate_external", "--bidirectional"),
        _script("explain"),
        _script("sensitivity"),
    ]
    for c in CONFIRMATORY:
        cmds += [_script("evaluate_confirmatory", c)]
        cmds += [_script("evaluate_confirmatory", c, "--feature-suffix", "_excl-PO3-PO4")]
    cmds += [
        _script("evaluate_combat"),
        _script("evaluate_aperiodic"),
        _script("evaluate_multisite"),
        _script("evaluate_clinical"),
        _script("evaluate_clinical_robustness"),
        _script("evaluate_without_ds002778"),
        _script("evaluate_qc_threshold"),
        _script("evaluate_qc_by_family"),
    ]
    return cmds


# Committed bundle -> freshly written table. metrics.json is assembled from parts.
METRICS_PARTS = {
    "internal_ds007526": "internal_baselines_ds007526.json",
    "external_a_to_b": "external_ds007526_to_ds002778.json",
    "external_b_to_a": "external_ds002778_to_ds007526.json",
    "dataset_shift": "dataset_shift.json",
}


def strip_volatile(obj: Any) -> Any:
    """Drop generation timestamps so only scientific content is compared."""
    if isinstance(obj, dict):
        return {k: strip_volatile(v) for k, v in obj.items() if k not in _VOLATILE_KEYS}
    if isinstance(obj, list):
        return [strip_volatile(v) for v in obj]
    return obj


def numeric_diffs(a: Any, b: Any, path: str = "") -> list[tuple[str, str]]:
    """List (path, description) for every leaf that differs between ``a`` and ``b``."""
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[tuple[str, str]] = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((f"{path}/{k}", "missing on one side"))
            else:
                out += numeric_diffs(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [(path, f"length {len(a)} vs {len(b)}")]
        return [
            d
            for i, (x, y) in enumerate(zip(a, b, strict=True))
            for d in numeric_diffs(x, y, f"{path}[{i}]")
        ]
    if a == b:
        return []
    if isinstance(a, int | float) and isinstance(b, int | float):
        return [(path, f"{a!r} vs {b!r} (|diff| {abs(a - b):.3g})")]
    return [(path, f"{a!r} vs {b!r}")]


@dataclass
class Check:
    name: str
    status: str  # "match", "differs" or "not produced"
    detail: str = ""


def compare(committed: Any, fresh: Any, name: str) -> Check:
    diffs = numeric_diffs(strip_volatile(committed), strip_volatile(fresh))
    if not diffs:
        return Check(name, "match")
    shown = "; ".join(f"{p} {d}" for p, d in diffs[:3])
    return Check(name, "differs", f"{len(diffs)} leaves differ, e.g. {shown}")


def verify_bundles(names: list[str]) -> list[Check]:
    checks = []
    for name in names:
        committed_path, fresh_path = BUNDLES / name, TABLES / name
        if not fresh_path.is_file():
            checks.append(Check(name, "not produced"))
            continue
        checks.append(
            compare(
                json.loads(committed_path.read_text()), json.loads(fresh_path.read_text()), name
            )
        )
    committed_metrics = json.loads((BUNDLES / "metrics.json").read_text())
    for key, table in METRICS_PARTS.items():
        label = f"metrics.json:{key}"
        if not (TABLES / table).is_file():
            checks.append(Check(label, "not produced"))
            continue
        checks.append(
            compare(committed_metrics[key], json.loads((TABLES / table).read_text()), label)
        )
    return checks


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def normalize_text(text: str) -> str:
    return _TIMESTAMP.sub("<timestamp>", text)


def verify_tracked_files() -> list[Check]:
    """Restore tracked files whose only change is a timestamp; report the rest."""
    checks = []
    for path in [p for p in _git("diff", "--name-only").splitlines() if p]:
        head = _git("show", f"HEAD:{path}")
        now = Path(path).read_text()
        if normalize_text(head) == normalize_text(now):
            Path(path).write_text(head)
            checks.append(Check(path, "match", "timestamp-only change restored"))
        else:
            checks.append(Check(path, "differs", "content differs from HEAD (left in place)"))
    return checks


def render_summary(
    mode: str, bundle_checks: list[Check], file_checks: list[Check], runtime_s: float
) -> str:
    lines = [
        "# Reproduction summary",
        "",
        f"Mode: `--from {mode}`. Runtime: {runtime_s / 60:.1f} min.",
        "",
        "## Result bundles vs committed `dashboard/data/` (timestamps ignored)",
        "",
        "| bundle | status | detail |",
        "| --- | --- | --- |",
    ]
    lines += [f"| {c.name} | {c.status} | {c.detail} |" for c in bundle_checks]
    lines += ["", "## Tracked files rewritten by the run", ""]
    if file_checks:
        lines += ["| file | status | detail |", "| --- | --- | --- |"]
        lines += [f"| {c.name} | {c.status} | {c.detail} |" for c in file_checks]
    else:
        lines.append("None.")
    n_match = sum(c.status == "match" for c in bundle_checks)
    lines += ["", f"{n_match}/{len(bundle_checks)} result bundles reproduced exactly.", ""]
    return "\n".join(lines)


def _bundle_names() -> list[str]:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_dashboard_data import BUNDLES as names

    return list(names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Re-run and verify NeuroPD analyses")
    parser.add_argument("--from", dest="start", choices=["features", "raw"], default="features")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)

    if _git("status", "--porcelain", "--untracked-files=no").strip():
        parser.error(
            "commit or stash tracked changes first, so the run's own changes can be verified"
        )

    t0 = time.time()
    if not args.verify_only:
        cmds = (raw_stage() if args.start == "raw" else []) + analysis_stage()
        for i, cmd in enumerate(cmds, 1):
            print(f"[{i}/{len(cmds)}] {' '.join(cmd[1:])}", flush=True)
            subprocess.run(cmd, check=True)
    summary = render_summary(
        args.start, verify_bundles(_bundle_names()), verify_tracked_files(), time.time() - t0
    )
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(summary)
    print(summary)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
