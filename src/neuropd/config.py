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
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class PreprocessingConfig(BaseModel):
    """Validated preprocessing parameters (spec Section 10).

    Values are the conservative defaults justified in
    ``docs/decisions/0005-preprocessing-pipeline.md`` after inspecting the data.
    The electrical line frequency is intentionally NOT here: it is per-dataset
    (ds002778 = 60 Hz, ds007526 = 50 Hz; see ADR 0004) and supplied at runtime.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = "conservative"
    bandpass_low_hz: float = Field(default=1.0, gt=0)
    bandpass_high_hz: float = Field(default=40.0, gt=0)
    apply_notch: bool = True
    resample_hz: float = Field(default=250.0, gt=0)
    reference: Literal["average"] = "average"
    montage: str = "standard_1005"
    epoch_length_s: float = Field(default=2.0, gt=0)
    epoch_overlap: float = Field(default=0.0, ge=0, lt=1)
    reject_peak_to_peak_uv: float | None = Field(default=150.0, gt=0)
    flat_peak_to_peak_uv: float | None = Field(default=1.0, ge=0)
    min_recording_duration_s: float = Field(default=60.0, ge=0)
    min_clean_epochs: int = Field(default=20, ge=1)

    @model_validator(mode="after")
    def _check_band(self) -> PreprocessingConfig:
        if self.bandpass_high_hz <= self.bandpass_low_hz:
            raise ValueError("bandpass_high_hz must exceed bandpass_low_hz")
        nyquist = self.resample_hz / 2.0
        if self.bandpass_high_hz >= nyquist:
            raise ValueError(
                f"bandpass_high_hz ({self.bandpass_high_hz}) must be < Nyquist "
                f"({nyquist}) of resample_hz ({self.resample_hz})"
            )
        return self


def load_preprocessing_config(path: str | Path | None = None) -> PreprocessingConfig:
    """Load and validate a preprocessing configuration (defaults when ``path`` is ``None``)."""
    if path is None:
        return PreprocessingConfig()
    return PreprocessingConfig.model_validate(load_yaml(path))


class PsdConfig(BaseModel):
    """Welch power-spectral-density estimation parameters (spec Section 12.1).

    ``window_s`` sets the segment length; frequency resolution is ``1 / window_s``
    Hz. With 2 s epochs the natural single-segment resolution is 0.5 Hz.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    method: Literal["welch"] = "welch"
    window_s: float = Field(default=2.0, gt=0)
    overlap: float = Field(default=0.5, ge=0, lt=1)
    fmax: float = Field(default=45.0, gt=0)


class SpectralFeatureConfig(BaseModel):
    """Which spectral features to compute (spec Section 12.1)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    absolute_power: bool = True
    relative_power: bool = True
    log_power: bool = True
    peak_alpha_frequency: bool = True
    spectral_edge_frequency: bool = True
    theta_alpha_ratio: bool = True
    delta_alpha_ratio: bool = True
    # Aperiodic slope/offset are added only if reliably estimable (Section 12.1);
    # None = not computed. Kept as an explicit tri-state for a later decision record.
    aperiodic: bool | None = None
    spectral_edge_quantile: float = Field(default=0.95, gt=0, lt=1)


class ComplexityFeatureConfig(BaseModel):
    """Which complexity features to compute (spec Section 12.2)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    spectral_entropy: bool = True
    permutation_entropy: bool = True
    hjorth: bool = True
    permutation_order: int = Field(default=3, ge=2, le=8)
    permutation_delay: int = Field(default=1, ge=1)


class ConnectivityFeatureConfig(BaseModel):
    """Optional connectivity features (spec Section 12.3); off for Milestone 3."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = False


AggStat = Literal["median", "iqr", "trimmed_mean", "std"]
_DEFAULT_AGG_STATS: tuple[AggStat, ...] = ("median", "iqr")


class AggregationConfig(BaseModel):
    """Epoch-to-participant aggregation (spec Section 12.4).

    Epoch-level features are reduced to one value per participant (per channel or
    region) using robust statistics. ``median`` captures central tendency;
    ``iqr`` captures within-participant variability.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    statistics: list[AggStat] = Field(default_factory=lambda: list(_DEFAULT_AGG_STATS))

    @model_validator(mode="after")
    def _non_empty_unique(self) -> AggregationConfig:
        if not self.statistics:
            raise ValueError("aggregation.statistics must not be empty")
        if len(set(self.statistics)) != len(self.statistics):
            raise ValueError(f"aggregation.statistics has duplicates: {self.statistics}")
        return self


class FeatureConfig(BaseModel):
    """Validated interpretable-feature configuration (spec Section 12).

    Frequency-band boundaries live here by design (Section 12.1). ``spatial``
    selects the harmonization strategy for the participant-level feature matrix
    (Section 11): ``region`` aggregates the shared channels into five scalp
    regions (fewer, montage-robust features); ``channel`` keeps one value per
    shared channel (more granular, for the harmonization comparison).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    bands: dict[str, tuple[float, float] | None]
    spectral: SpectralFeatureConfig = Field(default_factory=SpectralFeatureConfig)
    complexity: ComplexityFeatureConfig = Field(default_factory=ComplexityFeatureConfig)
    connectivity: ConnectivityFeatureConfig = Field(default_factory=ConnectivityFeatureConfig)
    aggregation: AggregationConfig = Field(default_factory=AggregationConfig)
    psd: PsdConfig = Field(default_factory=PsdConfig)
    spatial: Literal["region", "channel"] = "region"

    @model_validator(mode="after")
    def _check_bands(self) -> FeatureConfig:
        for name, band in self.bands.items():
            if band is None:
                continue
            lo, hi = band
            if lo <= 0:
                raise ValueError(f"band {name!r} lower edge must be > 0, got {lo}")
            if hi <= lo:
                raise ValueError(f"band {name!r} upper edge ({hi}) must exceed lower ({lo})")
        active = self.active_bands()
        if self.spectral.peak_alpha_frequency and "alpha" not in active:
            raise ValueError("peak_alpha_frequency requires an 'alpha' band to be defined")
        if self.spectral.theta_alpha_ratio and not {"theta", "alpha"} <= active.keys():
            raise ValueError("theta_alpha_ratio requires 'theta' and 'alpha' bands")
        if self.spectral.delta_alpha_ratio and not {"delta", "alpha"} <= active.keys():
            raise ValueError("delta_alpha_ratio requires 'delta' and 'alpha' bands")
        return self

    def active_bands(self) -> dict[str, tuple[float, float]]:
        """Return only the bands with defined (non-null) boundaries, in config order."""
        return {name: band for name, band in self.bands.items() if band is not None}


def load_feature_config(path: str | Path | None = None) -> FeatureConfig:
    """Load and validate a feature configuration.

    ``path`` defaults to ``configs/features/interpretable.yaml`` when ``None``.
    """
    if path is None:
        path = Path("configs/features/interpretable.yaml")
    return FeatureConfig.model_validate(load_yaml(path))


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
