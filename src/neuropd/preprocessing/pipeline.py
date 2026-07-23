"""Preprocessing pipeline orchestration (scaffold, Milestone 2).

Will assemble load -> standardize metadata -> select condition -> harmonize
channels -> montage -> filter/notch -> resample -> reference -> bad-channel
detection -> artifact handling -> epoching -> QC, driven entirely by
``configs/preprocessing/*.yaml``. Raw data remain immutable.
"""
