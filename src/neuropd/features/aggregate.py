"""Participant-level feature aggregation (scaffold, Milestone 3/Section 12.4).

Models ordinarily receive one feature vector per participant. Epoch-level
features are aggregated with robust statistics (median, IQR, trimmed mean,
within-participant variability). No participant IDs or labels enter the feature
matrix.
"""
