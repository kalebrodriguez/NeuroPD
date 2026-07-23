"""Smoke tests: package import, CLI, config, and provenance (spec Section 18.2)."""

from __future__ import annotations

import json

import neuropd
from neuropd.cli import main as cli_main
from neuropd.config import DEFAULT_SEED, ProjectConfig, load_project_config
from neuropd.provenance import collect_provenance


def test_package_imports() -> None:
    assert isinstance(neuropd.__version__, str)


def test_project_config_defaults_and_validation() -> None:
    cfg = ProjectConfig()
    assert cfg.seed == DEFAULT_SEED
    assert cfg.project_name == "neuropd"


def test_project_config_rejects_unknown_keys() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ProjectConfig.model_validate({"seed": 1, "unexpected": True})


def test_load_project_config_from_repo_file() -> None:
    from pathlib import Path

    cfg_path = Path(__file__).resolve().parents[1] / "configs" / "project.yaml"
    cfg = load_project_config(cfg_path)
    assert cfg.project_name == "neuropd"


def test_provenance_record_is_json_serialisable() -> None:
    rec = collect_provenance(seed=123)
    assert rec["seed"] == 123
    assert "packages" in rec and "numpy" in rec["packages"]
    json.dumps(rec)  # must not raise


def test_cli_provenance_runs(capsys) -> None:
    rc = cli_main(["provenance", "--seed", "7"])
    assert rc == 0
    out = capsys.readouterr().out
    assert json.loads(out)["seed"] == 7


def test_cli_no_args_prints_help(capsys) -> None:
    rc = cli_main([])
    assert rc == 0
    assert "NeuroPD" in capsys.readouterr().out
