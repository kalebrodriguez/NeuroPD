"""Tests for pure dataset-audit helpers (offline, spec Section 18)."""

from __future__ import annotations

from pathlib import Path

from neuropd.data.audit import (
    aggregate_recording_params,
    numeric_stats,
    participant_group,
    read_tsv,
    scalp_channels,
    summarize_demographics,
)


def test_read_tsv_handles_bom_and_ragged_rows(tmp_path: Path) -> None:
    p = tmp_path / "participants.tsv"
    content = "\ufeffparticipant_id\tage\tgroup\nsub-001\t60\tHC\nsub-002\t70\n"
    p.write_text(content, encoding="utf-8")
    rows = read_tsv(p)
    assert rows[0]["participant_id"] == "sub-001"
    assert rows[1]["group"] == ""  # missing trailing cell filled


def test_numeric_stats_ignores_missing() -> None:
    stats = numeric_stats(["60", "70", "n/a", ""])
    assert stats["n"] == 2
    assert stats["missing"] == 2
    assert stats["min"] == 60.0
    assert stats["max"] == 70.0


def test_participant_group_explicit_and_prefix() -> None:
    assert participant_group("sub-029", "PD") == "PD"
    assert participant_group("sub-hc1") == "HC"
    assert participant_group("sub-pd3") == "PD"
    assert participant_group("sub-001") is None  # numeric id needs explicit group


def test_summarize_demographics_prefix_mode() -> None:
    rows = [
        {"participant_id": "sub-hc1", "age": "50", "gender": "F"},
        {"participant_id": "sub-hc2", "age": "60", "gender": "M"},
        {"participant_id": "sub-pd3", "age": "70", "gender": "F"},
    ]
    summary = summarize_demographics(rows, group_col=None, age_col="age", sex_col="gender")
    assert summary["total"] == 3
    assert summary["HC"]["n"] == 2
    assert summary["PD"]["n"] == 1
    assert summary["HC"]["age"]["mean"] == 55.0
    assert summary["HC"]["sex"] == {"F": 1, "M": 1}


def test_scalp_channels_drops_non_scalp() -> None:
    rows = [
        {"name": "Fp1", "type": "EEG"},
        {"name": "Cz", "type": "EEG"},
        {"name": "EXG1", "type": "EEG"},
        {"name": "VREF", "type": "EEG"},
        {"name": "Status", "type": "TRIG"},
    ]
    assert scalp_channels(rows) == ["Fp1", "Cz"]


def test_aggregate_recording_params_counts_and_uniformity() -> None:
    jsons = [
        {
            "SamplingFrequency": 512.0,
            "PowerLineFrequency": 60,
            "EEGChannelCount": 40,
            "EEGReference": "n/a",
            "RecordingDuration": 192.0,
        },
        {
            "SamplingFrequency": 512.0,
            "PowerLineFrequency": 50,
            "EEGChannelCount": 40,
            "EEGReference": "n/a",
            "RecordingDuration": 200.0,
        },
    ]
    agg = aggregate_recording_params(jsons)
    assert agg["n_recordings"] == 2
    assert agg["sampling_frequency_hz"] == [512.0]
    assert agg["power_line_frequency_hz"] == [50, 60]
    assert agg["power_line_frequency_counts"] == {"60": 1, "50": 1}
    assert agg["recording_duration_s"]["mean"] == 196.0
