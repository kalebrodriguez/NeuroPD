"""Channel naming, montage, and harmonization (scaffold, Milestone 2/Section 11).

Will normalize channel names, compute the exact shared-channel subset across
datasets, and map electrodes to scalp regions (frontal/central/temporal/
parietal/occipital) for region-level aggregation. Shared channels must be derived
from real sidecars, never assumed (ds002778 vs the 64-channel EGI ds007526).
"""
