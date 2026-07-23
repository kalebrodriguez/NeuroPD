"""Feature assembly and participant-level aggregation (spec Sections 11, 12.4).

Turns clean epochs into ONE feature vector per participant:

1. Per (epoch, channel): compute interpretable base features (spectral +
   complexity). See ``spectral`` and ``complexity``.
2. Spatial reduction (harmonization strategy, Section 11):
   * ``region``  — average base features over the channels of each of the five
     scalp regions, giving montage-robust, count-controlled features.
   * ``channel`` — keep one value per shared channel (granular; for the
     harmonization comparison in Milestone 6).
3. Epoch reduction (Section 12.4): reduce over epochs with robust statistics
   (``median`` = central tendency, ``iqr`` = within-participant variability).

Feature names are ``{base}__{unit}__{stat}`` (e.g. ``rel_power_alpha__occipital__median``),
so region-by-frequency importance is directly readable later (Section 15).

No participant identifier or group label ever enters the feature values; labels
are carried in separate columns by the assembly layer (Section 6.3, Section 18.1).
"""

from __future__ import annotations

import numpy as np

from neuropd.config import FeatureConfig
from neuropd.data.regions import REGIONS, assign_region
from neuropd.features import complexity as cx
from neuropd.features import spectral as sp

NAME_SEP = "__"


def base_feature_names(cfg: FeatureConfig) -> list[str]:
    """Ordered names of the per-(epoch, channel) base features enabled by ``cfg``."""
    bands = cfg.active_bands()
    names: list[str] = []
    s = cfg.spectral
    if s.absolute_power:
        names += [f"abs_power_{b}" for b in bands]
    if s.relative_power:
        names += [f"rel_power_{b}" for b in bands]
    if s.log_power:
        names += [f"log_power_{b}" for b in bands]
    if s.peak_alpha_frequency:
        names.append("paf")
    if s.spectral_edge_frequency:
        names.append("sef")
    if s.theta_alpha_ratio:
        names.append("theta_alpha_ratio")
    if s.delta_alpha_ratio:
        names.append("delta_alpha_ratio")
    c = cfg.complexity
    if c.spectral_entropy:
        names.append("spectral_entropy")
    if c.permutation_entropy:
        names.append("perm_entropy")
    if c.hjorth:
        names += ["hjorth_activity", "hjorth_mobility", "hjorth_complexity"]
    return names


def _base_vector(sig: np.ndarray, sfreq: float, cfg: FeatureConfig) -> np.ndarray:
    """Compute the ordered base-feature vector for a single channel-epoch signal."""
    bands = cfg.active_bands()
    freqs, psd = sp.compute_psd(sig, sfreq, cfg.psd)
    abs_power = {b: sp.band_power(freqs, psd, lo, hi) for b, (lo, hi) in bands.items()}
    denom = float(np.nansum(list(abs_power.values())))

    out: list[float] = []
    s = cfg.spectral
    if s.absolute_power:
        out += [abs_power[b] for b in bands]
    if s.relative_power:
        out += [(abs_power[b] / denom) if denom > 0 else float("nan") for b in bands]
    if s.log_power:
        out += [np.log10(abs_power[b]) if abs_power[b] > 0 else float("nan") for b in bands]
    if s.peak_alpha_frequency:
        lo, hi = bands["alpha"]
        out.append(sp.peak_alpha_frequency(freqs, psd, lo, hi))
    if s.spectral_edge_frequency:
        out.append(sp.spectral_edge_frequency(freqs, psd, s.spectral_edge_quantile, cfg.psd.fmax))
    if s.theta_alpha_ratio:
        out.append(_safe_ratio(abs_power["theta"], abs_power["alpha"]))
    if s.delta_alpha_ratio:
        out.append(_safe_ratio(abs_power["delta"], abs_power["alpha"]))
    c = cfg.complexity
    if c.spectral_entropy:
        out.append(sp.spectral_entropy(freqs, psd, cfg.psd.fmax))
    if c.permutation_entropy:
        out.append(cx.permutation_entropy(sig, c.permutation_order, c.permutation_delay))
    if c.hjorth:
        out += list(cx.hjorth_parameters(sig))
    return np.asarray(out, dtype=float)


def _safe_ratio(num: float, den: float) -> float:
    return float(num / den) if den > 0 else float("nan")


def epoch_channel_features(data: np.ndarray, sfreq: float, cfg: FeatureConfig) -> np.ndarray:
    """Base features for every epoch and channel.

    ``data`` is ``(n_epochs, n_channels, n_times)``. Returns
    ``(n_epochs, n_channels, n_base_features)`` aligned with ``base_feature_names``.
    """
    if data.ndim != 3:
        raise ValueError(f"expected (n_epochs, n_channels, n_times), got {data.shape}")
    n_epochs, n_channels, _ = data.shape
    n_base = len(base_feature_names(cfg))
    out = np.empty((n_epochs, n_channels, n_base), dtype=float)
    for e in range(n_epochs):
        for ch in range(n_channels):
            out[e, ch] = _base_vector(data[e, ch], sfreq, cfg)
    return out


def _reduce_stat(values: np.ndarray, stat: str, axis: int) -> np.ndarray:
    """Robust reduction over ``axis`` ignoring NaNs. ``iqr`` is the 75-25 spread."""
    if stat == "median":
        return np.nanmedian(values, axis=axis)
    if stat == "iqr":
        q75, q25 = np.nanpercentile(values, [75, 25], axis=axis)
        return q75 - q25
    if stat == "std":
        return np.nanstd(values, axis=axis)
    if stat == "trimmed_mean":
        # 10% symmetric trim via percentile clipping, then nanmean.
        lo, hi = np.nanpercentile(values, [10, 90], axis=axis, keepdims=True)
        clipped = np.clip(values, lo, hi)
        return np.nanmean(clipped, axis=axis)
    raise ValueError(f"unknown aggregation statistic: {stat!r}")


def _region_indices(ch_names: list[str]) -> dict[str, list[int]]:
    """Map each scalp region to the indices of its channels (empty regions dropped)."""
    out: dict[str, list[int]] = {r: [] for r in REGIONS}
    for i, ch in enumerate(ch_names):
        region = assign_region(ch)
        if region is not None:
            out[region].append(i)
    return {r: idx for r, idx in out.items() if idx}


def participant_feature_row(
    data: np.ndarray, sfreq: float, ch_names: list[str], cfg: FeatureConfig
) -> dict[str, float]:
    """Assemble one participant's feature vector from pooled clean epochs.

    ``data`` is pooled ``(n_epochs, n_channels, n_times)`` across the participant's
    sessions; ``ch_names`` names the channels (same order). Returns a flat mapping
    of ``{base}__{unit}__{stat}`` to value.
    """
    if data.shape[1] != len(ch_names):
        raise ValueError(f"channel count {data.shape[1]} != len(ch_names) {len(ch_names)}")
    base = epoch_channel_features(data, sfreq, cfg)  # (n_epochs, n_channels, n_base)
    names = base_feature_names(cfg)

    if cfg.spatial == "region":
        region_idx = _region_indices(ch_names)
        units = list(region_idx)
        # Average base features over the channels of each region, per epoch.
        reduced = np.stack(
            [np.nanmean(base[:, idx, :], axis=1) for idx in region_idx.values()], axis=1
        )  # (n_epochs, n_regions, n_base)
    else:  # channel
        units = list(ch_names)
        reduced = base  # (n_epochs, n_channels, n_base)

    row: dict[str, float] = {}
    for stat in cfg.aggregation.statistics:
        stat_values = _reduce_stat(reduced, stat, axis=0)  # (n_units, n_base)
        for u, unit in enumerate(units):
            for f, fname in enumerate(names):
                row[f"{fname}{NAME_SEP}{unit}{NAME_SEP}{stat}"] = float(stat_values[u, f])
    return row


def feature_names(cfg: FeatureConfig, ch_names: list[str]) -> list[str]:
    """Full ordered list of participant-level feature-column names for ``cfg``."""
    names = base_feature_names(cfg)
    units = list(_region_indices(ch_names)) if cfg.spatial == "region" else list(ch_names)
    return [
        f"{fname}{NAME_SEP}{unit}{NAME_SEP}{stat}"
        for stat in cfg.aggregation.statistics
        for unit in units
        for fname in names
    ]
