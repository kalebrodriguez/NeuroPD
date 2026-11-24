# Reproducibility

`make reproduce` re-runs every analysis that writes a committed result, then checks
each fresh result against `dashboard/data/` (`scripts/reproduce.py`). Generation
timestamps are ignored. The script also checks every tracked document it rewrites:
a timestamp-only change is restored, and any other change is reported. It refuses
to run on a dirty working tree. `make reproduce-raw` does the same from raw EEG.
That run takes hours and rewrites the git-ignored derived data.

## Verification run (2026-11-24, `--from features`, executed in a cloud container)

**12 of 18 result bundles reproduced exactly.** Their documents matched apart from
timestamps.

These cover every analysis from the confirmatory cohorts onwards:
- confirmatory transfer, including the PO3/PO4-excluded variants (ADR 0013);
- ComBat (0014);
- aperiodic fit (0015);
- leave-one-site-out (0016);
- clinical (0017);
- clinical robustness (0018);
- without ds002778 (0019);
- QC threshold (0020);
- QC by family (0021).

**6 bundles differ. All are v0.1.0-era results computed on the original
210-feature matrix**, before the current 230-feature matrix. Re-running them on
the current features changes the numbers slightly. No conclusion changes:

| result | committed (210 features) | re-run (230 features) |
| --- | --- | --- |
| internal ROC-AUC, logreg / random forest / age+sex | 0.718 / 0.759 / 0.688 | 0.717 / 0.751 / 0.688 |
| site identity ds002778 vs ds007526 (logreg) | 0.953 | 0.952 |
| transfer ds007526 → ds002778, logreg | 0.671 | 0.720 (= the ADR 0014 value) |
| cross-dataset importance agreement r | 0.045 | 0.039 |
| `sensitivity.json` | — | 41 values differ. The channel-level matrices it needs were not extracted in this run. |

The affected bundles are `metrics.json` (internal, external both directions and
dataset shift), `feature_importance.json` and `sensitivity.json`. The report and
manuscript already disclose that the internal and ds002778-identity values come
from the 210-feature matrix. Refreshing these bundles to the current pipeline is an
owner decision, because it rewrites committed results.

Not covered by this run:
- preprocessing and feature extraction (`--from raw`);
- the channel-level matrices used by one ADR 0010 sensitivity arm.
