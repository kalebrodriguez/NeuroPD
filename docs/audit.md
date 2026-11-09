# Milestone 8 — Final Audit

Date: 2026-07-24. Audits the repository against the spec's completion standard
(Section 22 Milestone 8, Section 25, Section 31) before the `v0.1.0` release
candidate. Every check below was executed.

## Reproducibility audit

- **Environment locked:** `pyproject.toml`, `uv.lock`, `.python-version` (3.11) all
  present; dev tools are an optional group (`uv sync --extra dev`).
- **Determinism:** a central seed (`configs/project.yaml`, `DEFAULT_SEED=20240517`)
  is threaded through every stochastic step (CV shuffles, model `random_state`,
  bootstrap RNG).
- **Config-driven:** dataset, preprocessing, feature, and experiment parameters live
  in `configs/`, validated by Pydantic models that reject unknown keys.
- **Reproduction path (documented in README):** download → `preprocess.py` →
  `qc_report.py` → `extract_features.py` → `train.py` → `evaluate_external.py` →
  `explain.py` → `build_dashboard_data.py` → `streamlit run dashboard/app.py`.
- **CI:** GitHub Actions runs `ruff format --check`, `ruff check`, `mypy`, and
  `pytest` on every push, without downloading datasets. Status: green.
- **Tests:** 69 pass / 0 skip, including participant-isolation, no-leakage
  (scaler-in-fold, no id/label in the feature matrix), synthetic-signal feature
  checks, metrics toy examples, CV group-disjointness, and a headless dashboard run.

## Scientific-claims audit

Every headline number was re-verified against the executed `dashboard/data/metrics.json`:

| claim | source value |
|---|---|
| dataset-identity ROC-AUC ≈ 0.95 | 0.953 |
| dataset-identity balanced acc 0.833 | 0.833 |
| internal demographics balanced acc 0.645 | 0.645 |
| internal random-forest AUC 0.759 | 0.759 |
| external demographics balanced acc 0.500 | 0.500 |
| external logreg balanced acc 0.667 | 0.667 |

- No performance claim is stated that is not produced by executed code.
- Disallowed clinical language (Section 6.5) is not used; results are framed as
  research findings about cross-dataset robustness, never diagnosis.
- Predictive feature importance is explicitly distinguished from biological causation.

## Security / privacy audit

- **No raw or derived EEG is tracked in Git.** `git ls-files` shows only
  `data/raw/.gitkeep` under `data/`; no `.fif/.bdf/.set/.edf/.parquet`.
- **No secrets:** no `.env`, key, credential, or token files are tracked; `.env` is
  git-ignored and only `.env.example` exists.
- **Dashboard data is de-identified:** `dashboard/data/biomarkers.csv` carries no
  `participant_id` (enforced by a test); only dataset/group labels and derived
  feature values from public CC0 datasets.
- **No re-identification, no upload/prediction feature, no controlled-access data.**

## Credits / licensing audit

- Code: MIT (`LICENSE`). Datasets: CC0, cited with DOIs in `CITATION.cff`,
  `docs/dataset_audit.md`, and the README, including the ds002778 authors'
  pre-publication contact request.
- Software (MNE-Python, scikit-learn, NumPy/pandas/SciPy, Streamlit, etc.) is
  declared in `pyproject.toml`.

## AI-use note

Per the project owner, the `AI_USAGE.md` provenance file and README AI-use
disclosure were removed at their request; this is an owner decision for a personal
research/portfolio repository. If the work is later submitted where AI-use
disclosure is required, that line should be reinstated.

## Outcome

All Milestone 8 acceptance criteria are met: CI/tests pass, no secrets or raw data
are committed, all claims trace to executed analyses, and external data and software
are credited. Tagged as release candidate **v0.1.0**.


---

# v0.2.0 Release Audit

Date: 2026-11-08. Audits everything added since `v0.1.0`: sensitivity analyses,
harmonization (ADRs 0011, 0014), aperiodic features (ADRs 0012, 0015), confirmatory
cohorts (ADR 0013), and the site/dashboard refresh. Every check below was executed
in this session.

## Reproducibility
- **Environment:** `uv.lock` pins every dependency, including the one new runtime
  dependency, `fooof==1.1.1`. `neuropd --version` now reports `0.2.0`; it reported
  `0.0.0` before the fix below.
- **Re-execution:**
  - ds007526 and ds002778 were re-downloaded on 2026-11-08. File counts and sizes
    match the 2026-08-28 record.
  - Rebuilt features reproduce the committed 230-feature external results
    exactly: logreg ds007526→ds002778 balanced accuracy 0.633, AUC 0.720, and
    likewise for svm and random forest.
  - Dashboard biomarker values for the original cohorts differ only by float noise
    (relative ≤ 3e-10).
- **Pre-registration trail:** each of ADRs 0013, 0014 and 0015 was committed before
  its results. Deviations are dated in the ADRs and were decided from channel or
  event files only (PO3/PO4 interpolation; first eyes-open block).
- **Tests:** 110 pass. New tests cover:
  - cohort adapters (reference restore, interpolation, crop);
  - ComBat (scale equivariance, covariate preservation; numerically matched to
    `neuroCombat` in a throwaway environment);
  - spectral parameterization against synthetic spectra;
  - the new site and dashboard pages.

## Scientific claims
Fifteen headline numbers quoted in the README, ADRs 0013-0015 and `AGENTS.md` were
re-read programmatically from the result bundles in `dashboard/data/` and all match.
Examples:
- ds004584 H1 AUC 0.733 [0.643, 0.813]; sensitivity 0.740.
- ds003490 H1 AUC 0.591 [0.388, 0.785].
- ComBat criterion not met; specparam ds004584 d 0.52 [0.18, 0.89].
- specparam median R² 0.985 / 0.967 / 0.968 / 0.953.

Failed pre-declared criteria are reported as such: ds003490 H1, ComBat, and
specparam transfer. Language stays non-diagnostic.

## Security / privacy
- `git ls-files` shows only `.gitkeep` files under `data/`. No EEG or derived files
  (`.fif/.bdf/.set/.fdt/.edf/.vhdr/.parquet/.npy`) are tracked, and no
  `.env`/key/credential files.
- `.gitignore` covers the new raw cohorts, feature/aperiodic matrices and result
  tables (checked with `git check-ignore`).
- No participant identifiers appear on the 8 site pages or in `dashboard/data/`
  (grep for `sub-` tokens and a `participant_id` column; enforced by tests).
- Some docs (QC report, ADR 0013, research log) name the public datasets' own BIDS
  pseudonyms (for example `sub-019`) to document exclusions and deviations, as the
  v0.1.0 QC report already did. These are never published on the site.

## Credits / licensing
- All four datasets are CC0 and cited with DOIs in `CITATION.cff` and the README.
  The ds002778 pre-publication contact request is unchanged.
- Method papers were verified by web search for title, journal, volume and DOI:
  - Johnson et al. 2007 (doi:10.1093/biostatistics/kxj037);
  - Fortin et al. 2018 (doi:10.1016/j.neuroimage.2017.11.024);
  - Donoghue et al. 2020 (doi:10.1038/s41593-020-00744-x).
- A "Fortin et al. 2017" reference in ADR 0014 could not be verified and was
  removed.

## Outcome
All checks pass after two fixes made during the audit: the package version source,
and the unverifiable citation. The project is ready to tag as release candidate
**v0.2.0** once the owner approves tagging.


---

# v0.3.0 Release Audit

Date: 2026-11-09. Covers the work merged since `v0.2.0`: ADR 0016 (leave-one-site-out
multi-site training), ADR 0017 (within-PD clinical severity replication) and the
consolidated report. Every check below was executed.

- **Claims:** 12 headline numbers for ADRs 0016/0017 (LOSO arms A/B/C, svm
  0.680 → 0.840, theta/alpha r −0.260/−0.287 with p 0.008/0.007 and n 103/89, PAF
  r ≈ 0, motor +0.232/+0.197, exploratory 16/0 FDR hits with 59% sign agreement)
  were re-read from `dashboard/data/multisite.json` and `clinical.json`. All
  match.
- **Report:** `scripts/generate_report.py --check` passes; the committed
  `docs/report.md` equals a fresh rebuild from the result bundles.
- **Pre-registration trail:** ADRs 0016 and 0017 were each committed before their
  results (separate commits preceding the results commits).
- **Privacy/secrets:** no EEG or derived files tracked, no secret files, and no
  participant identifiers on the site, in `dashboard/data/` or in `docs/report.md`.
- **Tests:** `make check` passes (122 tests).
- **Outcome:** ready to tag as release candidate **v0.3.0**. Tag pushes are refused
  from the agent session (HTTP 403), so the owner pushes the tag. `v0.2.0` is also
  still owner-pending.
