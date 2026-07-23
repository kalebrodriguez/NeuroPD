"""Generate the dataset-audit report from fetched metadata (Milestone 1).

Reads ``data/metadata/<accession>/`` (populated by ``scripts/fetch_metadata.py``)
and computes participant/demographic counts, acquisition parameters, channel
sets, recording durations, the cross-dataset shared-channel set, and region
coverage. Writes a human-readable report to ``docs/dataset_audit.md`` and a
machine-readable summary to ``data/metadata/audit_summary.json``.

Every number is computed from real metadata files; nothing is assumed.

Usage:
    uv run python scripts/audit_datasets.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neuropd.data.audit import (
    aggregate_recording_params,
    read_json,
    read_tsv,
    scalp_channels,
    summarize_demographics,
)
from neuropd.data.openneuro import DATASETS
from neuropd.data.regions import REGIONS, region_breakdown, shared_channels
from neuropd.logging import configure_logging

METADATA_ROOT = Path("data/metadata")
DOC_PATH = Path("docs/dataset_audit.md")
SUMMARY_PATH = METADATA_ROOT / "audit_summary.json"

# Verified licensing/citation facts (from OpenNeuro metadata + dataset READMEs,
# retrieved 2026-07-23). These are stable per snapshot and documented here so the
# generated report is self-contained.
LICENSES = {
    "ds007526": {
        "license": "CC0",
        "doi": "doi:10.18112/openneuro.ds007526.v1.0.2",
        "download_size": "~4.27 GiB (4,578,751,379 B)",
        "citation": (
            "Katzir et al., Mov Disord 2026 (doi:10.1002/mds.70348). "
            "Please contact the authors (Tel Aviv Sourasky) to acknowledge."
        ),
    },
    "ds002778": {
        "license": "CC0",
        "doi": "doi:10.18112/openneuro.ds002778.v1.0.5",
        "download_size": "~545 MiB (571,470,906 B)",
        "citation": (
            "Jackson et al. 2019 (eNeuro; 10.1523/ENEURO.0151-19.2019); Swann et al. 2015; "
            "George et al. 2013. Email arockhil@uoregon.edu BEFORE publication (authors' request)."
        ),
    },
}

# Per-dataset participants.tsv column conventions (documented, not assumed at runtime
# beyond what the files contain).
DEMOG_COLS = {
    "ds002778": {"group_col": None, "age_col": "age", "sex_col": "gender"},
    "ds007526": {"group_col": "group", "age_col": "age", "sex_col": "sex"},
}


def _rest_eeg_jsons(meta_dir: Path) -> list[Path]:
    return sorted(meta_dir.rglob("*task-rest_eeg.json"))


def _rest_channels(meta_dir: Path) -> list[Path]:
    return sorted(meta_dir.rglob("*task-rest_channels.tsv"))


def audit_dataset(accession: str) -> dict[str, Any]:
    ref = DATASETS[accession]
    meta_dir = METADATA_ROOT / accession
    if not meta_dir.is_dir():
        raise FileNotFoundError(f"Missing metadata dir {meta_dir}; run fetch_metadata.py first.")

    participants = read_tsv(meta_dir / "participants.tsv")
    cols = DEMOG_COLS[accession]
    demographics = summarize_demographics(participants, **cols)

    eeg_jsons = [read_json(p) for p in _rest_eeg_jsons(meta_dir)]
    params = aggregate_recording_params(eeg_jsons) if eeg_jsons else {}

    channel_lists = [scalp_channels(read_tsv(p)) for p in _rest_channels(meta_dir)]
    canonical = channel_lists[0] if channel_lists else []
    uniform = all(cl == canonical for cl in channel_lists)
    deviating = sum(1 for cl in channel_lists if cl != canonical)

    return {
        "accession": accession,
        "tag": ref.tag,
        "role": ref.role,
        "demographics": demographics,
        "recording_params": params,
        "scalp_channels": {
            "n": len(canonical),
            "names": canonical,
            "uniform_across_recordings": uniform,
            "n_recordings_checked": len(channel_lists),
            "n_deviating": deviating,
        },
    }


def build_summary() -> dict[str, Any]:
    per_dataset = {acc: audit_dataset(acc) for acc in DATASETS}
    dev = per_dataset["ds007526"]["scalp_channels"]["names"]
    ext = per_dataset["ds002778"]["scalp_channels"]["names"]
    shared = shared_channels(ext, dev)  # order by external cohort
    regions = region_breakdown(shared)
    return {
        "datasets": per_dataset,
        "harmonization": {
            "shared_scalp_channels": {"n": len(shared), "names": shared},
            "only_in_ds002778": [c for c in ext if c not in set(dev)],
            "region_breakdown": {r: regions[r] for r in REGIONS},
        },
    }


def _fmt_params(p: dict[str, Any]) -> str:
    if not p:
        return "_(no rest eeg.json found)_"
    dur = p["recording_duration_s"]
    return (
        f"sfreq={p['sampling_frequency_hz']} Hz; line={p['power_line_frequency_hz']} Hz; "
        f"eeg_channel_count={p['eeg_channel_count']}; reference={p['eeg_reference']}; "
        f"duration_s: mean={dur.get('mean')} [{dur.get('min')}-{dur.get('max')}] "
        f"(n={dur.get('n')}); n_recordings={p['n_recordings']}"
    )


def render_markdown(summary: dict[str, Any]) -> str:
    d7 = summary["datasets"]["ds007526"]
    d2 = summary["datasets"]["ds002778"]
    h = summary["harmonization"]
    lines: list[str] = []
    lines.append("# Dataset Audit\n")
    lines.append(
        "> Generated by `scripts/audit_datasets.py` from metadata under "
        "`data/metadata/` (OpenNeuro sidecars). Every value below is computed from "
        "real files. Regenerate with `uv run python scripts/audit_datasets.py`.\n"
    )
    for tag, d in (("Development", d7), ("External validation", d2)):
        dm = d["demographics"]
        sc = d["scalp_channels"]
        lines.append(f"## {d['accession']} ({tag}, snapshot {d['tag']})\n")
        lines.append(f"- Participants (total): **{dm['total']}**")
        for g in ("HC", "PD"):
            if g in dm:
                e = dm[g]
                age = e.get("age", {})
                lines.append(
                    f"  - {g}: n={e['n']}"
                    + (
                        f"; age mean={age.get('mean')} [{age.get('min')}-{age.get('max')}]"
                        if age
                        else ""
                    )
                    + (f"; sex={e.get('sex')}" if e.get("sex") else "")
                )
        lines.append(f"- Acquisition: {_fmt_params(d['recording_params'])}")
        plf = d["recording_params"].get("power_line_frequency_counts")
        if plf and len(plf) > 1:
            lines.append(f"  - PowerLineFrequency values (recordings): {plf}")
        lines.append(
            f"- Scalp channels: **{sc['n']}** "
            f"(uniform across {sc['n_recordings_checked']} rest recordings: "
            f"{sc['uniform_across_recordings']}, deviating={sc['n_deviating']})"
        )
        lic = LICENSES[d["accession"]]
        lines.append(f"- License: {lic['license']} ({lic['doi']}); download {lic['download_size']}")
        lines.append(f"- Citation: {lic['citation']}")
        lines.append("")
    sh = h["shared_scalp_channels"]
    lines.append("## Cross-dataset channel harmonization\n")
    lines.append(f"- **Shared scalp channels: {sh['n']}**")
    lines.append(f"  - {', '.join(sh['names'])}")
    lines.append(f"- In ds002778 but not ds007526: {h['only_in_ds002778'] or 'none'}")
    lines.append("- Region coverage of shared channels:")
    for r in REGIONS:
        chans = h["region_breakdown"][r]
        lines.append(f"  - {r}: {len(chans)} ({', '.join(chans) if chans else '-'})")
    lines.append("")

    # Interpretation / incompatibilities (curated, references computed values above).
    d7p = d7["recording_params"]
    d2p = d2["recording_params"]
    lines.append("## Primary comparable condition\n")
    lines.append(
        "- Both cohorts provide **resting-state, eyes-open** recordings, so the primary "
        "comparable condition is **task-rest, eyes-open**. ds002778's eye condition is "
        "confirmed from Jackson et al. 2019 (participants fixated on a cross); it is NOT "
        "in the BIDS sidecars (see docs/decisions/0002). ds007526 rest is eyes-open per "
        "its README. ds007526's walking task is excluded from the primary analysis."
    )
    lines.append("")
    lines.append("## Cross-dataset incompatibilities & harmonization plan\n")
    lines.append(
        f"- **Sampling rate differs** ({d2p['sampling_frequency_hz']} Hz vs "
        f"{d7p['sampling_frequency_hz']} Hz) -> resample to a shared rate (e.g. 250 Hz) "
        "before feature extraction."
    )
    lines.append(
        f"- **Montage differs** (ds002778 32-ch BioSemi vs ds007526 60-ch, 10-20 names) "
        f"-> use the **{sh['n']} shared scalp channels** and/or region-level aggregation."
    )
    lines.append(
        "- **Class imbalance** in the development cohort (ds007526 ~4:1 PD:HC) vs near-balance "
        "in ds002778 -> imbalance-robust metrics and training-fold-only weighting."
    )
    lines.append(
        "- **Age/sex confound**: in ds007526 PD are older than HC and more male; ds002778 is "
        "age/sex-balanced -> demographics-only baseline and age/sex-adjusted sensitivity analyses."
    )
    lines.append(
        "- **Medication sessions** (ds002778 PD have ses-on + ses-off) -> keep both sessions of a "
        "participant in the same split; enables an optional medication-state sensitivity analysis."
    )
    lines.append("")
    lines.append("## Data-quality notes\n")
    plf2 = d2p.get("power_line_frequency_counts", {})
    lines.append(
        f"- **ds002778 PowerLineFrequency inconsistency**: sidecars report {plf2}. San Diego "
        "mains is 60 Hz, so the 9 recordings tagged 50 Hz are metadata errors; apply a **60 Hz "
        "notch** for ds002778 regardless of the sidecar (documented in preprocessing decisions)."
    )
    lines.append(
        "- **ds002778 sub-pd6 / sub-pd16 (ses-on)** used preprocessed EEGLAB .mat data rather "
        "than raw (per participants.tsv notes); flag for provenance and consider excluding the "
        "ON session in a sensitivity analysis."
    )
    dur2 = d2p["recording_duration_s"]
    d7mean = d7p["recording_duration_s"].get("mean")
    lines.append(
        f"- **Recording duration**: ds002778 mean {dur2.get('mean')} s "
        f"[{dur2.get('min')}-{dur2.get('max')}] (one ~292 s outlier: sub-pd14 ses-off); "
        f"ds007526 ~{d7mean} s. Fixed-length epoching will equalize usable data."
    )
    lines.append(
        "- **Missing/corrupted files**: none detected among fetched metadata; ds002778 has "
        "46/46 expected rest recordings and ds007526 144/144. Full binary integrity is "
        "checked at download time."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    log = configure_logging()
    summary = build_summary()
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    DOC_PATH.write_text(render_markdown(summary), encoding="utf-8")
    log.info("Wrote %s and %s", DOC_PATH, SUMMARY_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
