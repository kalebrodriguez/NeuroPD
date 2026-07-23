"""Configuration loading and validation for NeuroPD.

All scientifically meaningful parameters live in YAML configuration files under
``configs/`` rather than being scattered through the code (spec Section 7 and
Section 24). This module provides:

* a strict YAML loader, and
* Pydantic models that validate configuration and *fail loudly* on invalid or
  unexpected fields.

During Milestone 0 only the small, cross-cutting settings are modelled (project
metadata and the central random seed). Dataset, preprocessing, feature, and
experiment schemas are added in their respective milestones so that validation
always reflects real, inspected parameters rather than assumptions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

# Central default seed. Every stochastic operation must derive from a configured
# seed so that runs are reproducible (spec Section 7).
DEFAULT_SEED = 20240517


class ProjectConfig(BaseModel):
    """Top-level, cross-cutting project settings.

    Attributes
    ----------
    seed:
        Central random seed propagated to NumPy, scikit-learn, and any other
        stochastic component.
    project_name:
        Human-readable project identifier used in run metadata.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    seed: int = Field(default=DEFAULT_SEED, ge=0)
    project_name: str = Field(default="neuropd", min_length=1)


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file into a dictionary, failing loudly on problems.

    Parameters
    ----------
    path:
        Path to a ``.yaml``/``.yml`` file.

    Returns
    -------
    dict
        Parsed mapping.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the file does not contain a top-level mapping.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Configuration file not found: {p}")
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping at the top level of {p}, got {type(data).__name__}")
    return data


def load_project_config(path: str | Path | None = None) -> ProjectConfig:
    """Load and validate the project configuration.

    Parameters
    ----------
    path:
        Optional path to a YAML file. When ``None``, defaults are used. Unknown
        keys are rejected (``extra="forbid"``) so that typos surface immediately.
    """
    if path is None:
        return ProjectConfig()
    return ProjectConfig.model_validate(load_yaml(path))
