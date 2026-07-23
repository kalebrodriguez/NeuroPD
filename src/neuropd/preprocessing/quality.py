"""Quality-control metrics and exclusion accounting (scaffold, Milestone 2/Section 10.3).

Will record participant- and epoch-level QC (usable epochs, bad-channel counts,
rejection rates, durations) and produce an exclusion table with reasons.
Participants are never excluded because their data weakens model performance.
"""
