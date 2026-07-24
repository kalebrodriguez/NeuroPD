# Research Log

Chronological record of work sessions (spec Section 21). Failed attempts are kept,
not erased. Entries distinguish planned / exploratory / confirmatory analyses.

---

## 2026-07-23 — Section 29 initial investigation

- **Goal:** Execute Section 29 (inspect repo/environment, verify dataset metadata,
  propose Milestone 0). No downloads, training, or publishing.
- **Work completed:** Inspected repository (only `AGENTS.md` + `README.md`
  present; repo is public). Captured Cloud VM environment (Ubuntu 24.04, 4 vCPU,
  15 GiB RAM, ~235 GB free, no GPU, system Python 3.12, no `uv`). Verified
  OpenNeuro metadata live via GraphQL and fetched each dataset's
  `participants.tsv`/`README` (KB-scale metadata only).
- **Results (executed):**
  - ds002778 v1.0.5 — 571,470,906 B (~545 MiB), CC0, 31 participants (16 HC / 15
    PD); task rest; PD have ses-on + ses-off, HC have ses-hc. README explicitly
    cautions against small-sample PD-vs-HC classification and requests
    pre-publication contact.
  - ds007526 v1.0.2 — 4,578,751,379 B (~4.27 GiB), CC0, 144 participants (28 HC /
    116 PD); tasks rest (eyes-open, ~4 min) + walk; 64-ch EGI; rich clinical data.
- **Decisions (owner-approved):** development = ds007526; external validation =
  ds002778; framing = cross-dataset generalization/robustness, not diagnosis;
  keep repo public with strict data `.gitignore`; environment = uv + Python 3.11.
- **Questions/next:** Milestone 1 begins with verifying the ds002778 eye condition
  (do not assume it matches ds007526's eyes-open).

---

## 2026-07-23 — Milestone 0: repository & environment

- **Goal (planned):** Scaffold the repository, configure the uv/Python 3.11
  environment, add data-safety protections and documentation, wire tooling/CI,
  and pass required checks. No data, no models.
- **Work completed:** Created the package skeleton under `src/neuropd/`;
  implemented `config`, `logging`, `provenance`, CLI, and the participant-isolation
  guardrail with tests; authored `pyproject.toml` and generated `uv.lock`; added
  `.gitignore`/`.env.example`; created verified dataset configs and provisional
  preprocessing/feature/experiment configs; added governance docs and GitHub
  Actions CI.
- **Commands run:** recorded in the Milestone 0 report (uv sync, ruff, mypy, pytest).
- **Results:** see the Milestone 0 report and PR. No datasets downloaded.
- **Next step:** await owner review; then Milestone 1 (dataset audit).

---

## 2026-07-23 — Milestone 1: dataset audit

- **Goal:** Audit both datasets from real metadata. First task (owner-prioritized):
  verify the ds002778 eye condition. No full-dataset download; no training.
- **Work completed:**
  - Built a reproducible, stdlib-only OpenNeuro metadata client
    (`neuropd.data.openneuro`) that traverses the snapshot tree and downloads
    **only** small `*.json`/`*.tsv` sidecars (binary recordings are refused).
  - Added pure audit/region helpers (`neuropd.data.audit`, `neuropd.data.regions`)
    with offline unit tests; scripts `fetch_metadata.py` and `audit_datasets.py`.
  - Fetched metadata: 280 files for ds002778 (all 46 rest recordings) and 1011 for
    ds007526 (all 144 rest recordings) into `data/metadata/` (git-ignored).
  - Generated `docs/dataset_audit.md` + `data/metadata/audit_summary.json`.
- **Results (executed / confirmatory):**
  - **Eye condition:** BOTH eyes-open. ds007526 per README; ds002778 verified from
    Jackson et al. 2019 ("fixate on a cross"). Not in ds002778 sidecars. No mismatch.
  - **ds007526:** 144 (28 HC / 116 PD); 250 Hz; 50 Hz line; 60 scalp channels
    (uniform); duration ~242 s. HC age 60.8 [42-72] (13M/15F); PD 66.1 [39-84] (72M/44F).
  - **ds002778:** 31 (16 HC / 15 PD); 512 Hz; 60 scalp+EXG; 32 scalp (uniform over 46);
    duration ~197 s. HC age 63.5, PD 63.3 (both ~balanced sex).
  - **Shared scalp channels: 31** (all ds002778 scalp except Cz = EGI VREF); covers all
    5 regions.
- **Errors/unexpected findings:**
  - ds002778 `PowerLineFrequency` inconsistent: 37×60 Hz, 9×50 Hz (metadata error; San
    Diego is 60 Hz) -> ADR 0004 (notch at 60 Hz).
  - Age/sex confound present in development cohort (PD older, more male).
  - GraphQL `untracked` arg invalid (400); `RemoteDisconnected` is `OSError` not
    `URLError` — broadened retry handling and made downloads non-fatal/resumable.
- **Decisions:** ADR 0002 updated (eyes-open verified); ADR 0004 added (line freq/notch).
- **Next step:** owner review of the audit; on approval, Milestone 2 (preprocessing).
  Full raw-data download still requires explicit approval.

---

## 2026-07-23 — Milestone 2: raw download + preprocessing

- **Goal:** With owner approval, download raw data and build the configurable
  conservative preprocessing pipeline; run end-to-end on a subset.
- **Work completed:**
  - Approval-gated downloader (`download_dataset`); fetched ds002778 (331 files,
    545.0 MiB) and ds007526 rest-only (1160 files, 2172.8 MiB) into git-ignored
    `data/raw/`, checksummed (SHA-256), set read-only; provenance in
    `docs/data_provenance.md`.
    Verified MNE loads (ds002778 512 Hz/41 ch; ds007526 250 Hz/65 ch).
  - Preprocessing pipeline (`neuropd.preprocessing.*`): shared-channel harmonization
    (31 ch), montage, per-dataset notch (ADR 0004), 1-40 Hz band-pass, resample 250 Hz,
    average reference, 2 s epochs, 150 µV rejection, predeclared exclusion. Config
    validated by `PreprocessingConfig`. Loaders in `neuropd.data.loaders`.
  - `scripts/preprocess.py`; QC tables + PSD figures (git-ignored). 7 synthetic tests.
- **Results (executed):**
  - ds007526 subset: ~94-98% epochs kept. ds002778 subset: PD ses off/on ~83-91% kept;
    HC ~43-53% kept (higher rejection at 150 µV; still >40 clean epochs, none excluded).
  - PSD figures visually inspected: clear alpha (~10-12 Hz), 1/f slope, 1/40 Hz band
    edges, no line-noise spike. Both PD sessions of sub-pd11 processed (kept together).
- **Decisions:** ADR 0005 (conservative pipeline). Confirmed ADR 0004 with owner.
- **Errors/findings:** synthetic tests initially failed because a spatially uniform
  signal is cancelled by the average reference — corrected the synthetic generator to
  vary per channel (a useful reminder of what average referencing does).
- **Next step:** owner review; then run preprocessing on the full cohorts to produce
  the committed QC/exclusion report, and proceed to Milestone 3 (features).

---

## 2026-07-23 — Local setup + full-cohort QC + Milestone 3 (features)

- **Goal (planned):** Set up the project on the owner's local Mac (this is where the
  rest of the work happens), run full-cohort preprocessing to produce the committed
  QC/exclusion report, and implement Milestone 3 (interpretable participant-level
  features). Also (owner request) remove `AI_USAGE.md` and the AI-use disclosure.
- **Environment:** Fresh clone on macOS (Darwin 25.4); `uv sync --extra dev` built the
  pinned Python 3.11 env. Re-downloaded raw data (owner-approved) via the gated
  downloader — ds002778 545.0 MiB / 331 files, ds007526 rest-only 2172.8 MiB / 1160
  files — sizes/counts match the Milestone 2 cloud provenance exactly.
- **Work completed:**
  - **Features (`neuropd.features`):** `spectral.py` (Welch PSD; absolute/relative/log
    band power, peak alpha frequency, 95% spectral edge frequency, theta/alpha &
    delta/alpha ratios, spectral entropy), `complexity.py` (Hjorth activity/mobility/
    complexity, Bandt-Pompe permutation entropy), `aggregate.py` (epoch×channel base
    features → region-level spatial aggregation → per-participant median/IQR),
    `matrix.py` (one-row-per-participant assembly with identifiers/labels kept
    physically separate). `FeatureConfig` added to `config.py`; feature YAML expanded
    (PSD params, spatial strategy; **gamma disabled** — attenuated by the 1-40 Hz band-pass).
  - **Scripts:** `extract_features.py` (processed epochs → matrix, sessions pooled),
    `qc_report.py` (committed QC report from the QC tables).
  - **Docs:** ADR 0006 (feature decisions), `docs/feature_dictionary.md`,
    `docs/preprocessing_qc.md`, limitations updated. Removed `AI_USAGE.md` + all refs
    and the README AI-use disclosure.
  - **Tests:** 11 new synthetic/leakage tests (planned + confirmatory). Full suite
    41 passing / 2 skipped (M4); ruff + mypy clean.
- **Results (executed):**
  - **QC (confirmatory):** ds007526 144 recordings, **11 excluded** (10 PD, 1 HC);
    retained 27 HC / 106 PD. ds002778 46 recordings, **1 excluded** (HC sub-hc25);
    retained 15 HC / 15 PD.
  - **Features:** ds007526 = 133 participants × 210 features (0 NaN); ds002778 = 30 ×
    210 (0 NaN). PD have 2 sessions pooled in ds002778.
  - **Exploratory (not confirmatory):** occipital peak alpha frequency is lower in PD
    in BOTH datasets (ds007526 9.0 vs HC 9.6; ds002778 9.6 vs HC 9.8) and central
    theta/alpha ratio slightly higher in PD — directionally consistent with spectral
    slowing. No statistics run; not to be interpreted as a result.
- **Errors/unexpected findings (kept):**
  - NumPy 2.4 removed `np.trapz` and `np.math.factorial` — switched to `np.trapezoid`
    and `math.factorial`.
  - **PD-concentrated QC exclusion:** the 10 excluded ds007526 PD recordings are
    genuinely high-amplitude (post-filter median worst-channel p2p ≈ 325-388 µV, 100%
    of epochs > 150 µV) — verified NOT a units bug (raw amplitudes are plausible µV).
    The predeclared 150 µV threshold was deliberately NOT loosened; documented as a
    limitation with a proposed lenient-threshold/ICA sensitivity analysis.
- **Decisions:** ADR 0006 (region-level features, gamma off, sessions pooled, median/IQR).
- **Next step:** owner review of Milestone 3; then Milestone 4 (internal baselines:
  majority, demographics-only, regularized logistic regression, linear SVM, random
  forest) with participant-safe group cross-validation.

---

## 2026-07-23 — Milestone 4: internal baselines

- **Goal (planned):** Implement and run the required baselines on the development
  cohort (ds007526) under participant-safe cross-validation, with participant-level
  bootstrap CIs. External cohort untouched (frozen for M5).
- **Decisions (owner-approved + ADR 0007):** flat repeated stratified grouped 5-fold
  CV (5 repeats) keyed by participant; minimal tuning (no nested CV); primary metric
  = balanced accuracy; `class_weight="balanced"` fitted in-fold; 95% participant-level
  bootstrap CIs (2000 resamples). Owner chose "merge PR #5 now" — M3 merged to main,
  this M4 branch rebased onto it.
- **Work completed:**
  - `evaluation/metrics.py` (balanced accuracy, ROC-AUC, sensitivity, specificity,
    F1, confusion counts; PD = positive), `evaluation/bootstrap.py` (participant
    resampling CIs), `modeling/baselines.py` (5 baselines as sklearn Pipelines with
    in-fold impute/scale), `modeling/pipeline.py` (grouped-CV runner asserting
    participant disjointness per fold, out-of-fold predictions averaged over repeats).
  - `scripts/train.py`; experiment config filled in; ADR 0007; committed results
    `docs/internal_baselines.md`.
  - Tests: `test_metrics.py` (un-skipped), `test_modeling.py` (new), scaler-in-fold
    leakage test (un-skipped). Full suite 56 pass / 0 skip; ruff format+check+mypy clean.
- **Results (executed, ds007526, 106 PD / 27 HC, 210 features):**
  - majority: balanced acc 0.500 / AUC 0.500.
  - **demographics (age+sex): balanced acc 0.645 [0.539, 0.745], AUC 0.688** —
    **exceeds all EEG models on balanced accuracy.**
  - logreg: bal acc 0.563, AUC 0.718 | svm_linear: 0.558, 0.662 | random_forest:
    0.591, AUC 0.759 [0.660, 0.847].
  - EEG models have high sensitivity (~0.78-0.85) but low specificity (~0.33): they
    lean toward the PD majority. Demographics is more balanced (sens 0.66 / spec 0.63).
- **Interpretation (confirmatory of a confound, not of EEG utility):** age/sex alone
  carry substantial signal because ds007526 PD are older and more male than HC. EEG
  features add ranking ability (AUC) but their decision-level (balanced-accuracy)
  separation is partly confounded. Reported honestly; motivates age/sex-adjusted
  sensitivity analyses and the external-transfer test.
- **Next step:** owner review of Milestone 4; then Milestone 5 (frozen external
  evaluation: train on ds007526, test on ds002778; generalization gap; calibration).

---

## 2026-07-24 — Milestone 5: frozen external evaluation

- **Goal (planned, confirmatory):** the project's central test — fit each frozen
  baseline on the full development cohort and evaluate once on the full external
  cohort; quantify the generalization gap and calibration. No tuning on the external
  cohort. Owner said "next" -> merged PR #6 (M4) to main, branched M5 off it.
- **Work completed:** `evaluation/transfer.py` (fit-on-dev/predict-on-external +
  generalization gap), `modeling/calibration.py` (Brier + reliability curve),
  `neuropd/data/demographics.py` (shared age/sex loader; refactored out of train.py),
  `scripts/evaluate_external.py` (both directions), ADR 0008, committed results
  `docs/external_transfer.md`, `tests/test_transfer.py`. Full suite 59 pass / 0 skip;
  ruff format+check + mypy clean.
- **Results (executed, primary ds007526 -> ds002778; external n=30):**
  - demographics: internal bal_acc 0.645 -> **external 0.500 (chance)**, AUC 0.538.
  - logreg: internal 0.563 -> external 0.667, AUC 0.671 [0.45, 0.86].
  - svm_linear: internal 0.558 -> external 0.633, AUC 0.653.
  - random_forest: internal 0.591 -> external 0.533, AUC 0.738 (high AUC, poor
    balanced accuracy -> threshold/calibration issue; Brier 0.231).
  - Reverse (ds002778 -> ds007526, exploratory, tiny train): RF internal 0.800 ->
    external 0.588 (gap +0.212, overfitting on n=30); linear models ~0.66-0.67 external.
- **Interpretation (confirmatory):**
  1. **The demographic confound does NOT transfer** — age/sex separated groups within
     ds007526 but collapsed to chance on the balanced ds002778, confirming the internal
     demographics result was cohort-specific confounding.
  2. **Linear EEG models transfer modestly** (~0.63-0.67 external bal_acc, no
     degradation vs internal) — some cross-cohort robustness of interpretable features.
  3. **BUT** external n=30 gives wide CIs that include chance — NOT statistically
     conclusive. Reported honestly; no optimization toward a desired result.
  4. Random forest generalizes worst on decision accuracy — simpler models more robust
     (Section 3.2 Q4).
- **Next step:** owner review of Milestone 5; then Milestone 6 (explainability +
  sensitivity: feature-importance stability, age/sex-adjusted + harmonization
  sensitivity analyses, unsupervised dataset-shift check).

---

## 2026-07-24 — Milestone 6: explainability + dataset-shift

- **Goal (planned + exploratory):** interpret the M5 transfer result — feature-
  importance stability and, critically, test whether dataset identity is more
  predictable than disease (Section 16). Owner said "go" -> merged PR #7 (M5), branched
  M6 off main.
- **Work completed:** `modeling/explainability.py` (fold-stable standardized logreg
  coefficients, region×frequency aggregation, cross-dataset agreement),
  `scripts/explain.py` (feature importance + dataset-shift), ADR 0009, committed
  `docs/explainability.md` + `docs/dataset_shift.md`, `tests/test_explainability.py`.
  Full suite 62 pass / 0 skip; ruff format+check + mypy clean.
- **Results (executed) — the central methodological finding:**
  - **Dataset-identity prediction: logreg balanced_acc 0.833, ROC-AUC 0.953; RF AUC
    0.894** — FAR above disease predictability (~0.72 internal, ~0.65 external).
  - **Cross-dataset feature-importance agreement: Pearson r = +0.045** (~0) — the model
    uses different features in each cohort.
  - Top ds007526 disease features are fold-stable (sign consistency 1.0), dominated by
    within-participant variability (IQR) of occipital/frontal theta/beta power and PAF spread.
- **Interpretation:** the shared EEG feature space is **dominated by site/acquisition
  differences, not disease physiology** — dataset identity is ~AUC 0.95 vs disease
  ~0.72, and disease features don't agree across cohorts. This explains the limited
  M5 transfer and is the project's key transparency result. It is about dataset shift,
  NOT brain biology (no causal/clinical claim).
- **Deferred (proposed for follow-up):** shared-channel-vs-region and age/sex-adjusted
  sensitivity analyses, RF permutation importance, ComBat-style harmonization.
- **Next step:** owner review of Milestone 6; then Milestone 7 (dashboard + portfolio)
  or the deferred sensitivity analyses.

---

## 2026-07-24 — Milestone 7: educational dashboard

- **Goal (planned):** build the Streamlit dashboard on precomputed, de-identified
  outputs (Section 17). Owner said "next" -> merged PR #8 (M6), branched M7 off main.
  No deployment yet (deferred per roadmap; requires owner approval).
- **Work completed:** `scripts/build_dashboard_data.py` writes committed, de-identified
  artifacts to `dashboard/data/` (metrics.json, cohorts.json, biomarkers.csv — **no
  participant ids**); `dashboard/app.py` rewritten as a 6-page Streamlit app (overview,
  dataset explorer, biomarker explorer, model evaluation, generalization gap +
  dataset-shift, methods/limitations) reading only that data, with the non-diagnostic
  disclaimer on every page. Added JSON output to `explain.py` (dataset_shift.json).
  `tests/test_dashboard.py` runs the app headlessly (Streamlit AppTest) across all
  pages and checks the committed data carries no participant id. Full suite 69 pass /
  0 skip; ruff format+check + mypy clean.
- **Results (executed):** dashboard data built (163 de-identified biomarker rows);
  all 6 pages render without error under AppTest; disclaimer present on every page.
- **Guardrails honored:** dashboard uses only derived, de-identified results; runs
  without raw EEG; no upload/prediction feature; sample sizes shown beside metrics;
  exploratory plots labeled. **Not deployed** (GitHub Pages / Heroku deployment is a
  separate, owner-approved step).
- **Next step:** owner review of Milestone 7; then optionally deploy (Milestone 7
  deployment), run deferred sensitivity analyses, or Milestone 8 (final audit).

---

## 2026-07-24 — Milestone 8: final audit + v0.1.0 release candidate

- **Goal (planned):** final reproducibility / scientific-claims / security-privacy /
  credits audit; cut a versioned release candidate. Owner said "next" -> merged PR #9
  (M7), branched M8 off main.
- **Work completed:** `docs/audit.md` (all four audits, executed); bumped version to
  **0.1.0** (`pyproject.toml`, `CITATION.cff` + date-released); CHANGELOG `[0.1.0]`
  release section.
- **Results (executed):**
  - Security/privacy: only `data/raw/.gitkeep` tracked under `data/` — no raw/derived
    EEG, no `.env`/secrets; dashboard CSV verified to carry no participant id.
  - Scientific claims: every headline number re-verified against
    `dashboard/data/metrics.json` (dataset-shift AUC 0.953; internal demographics
    0.645; external demographics 0.500; external logreg 0.667; etc.) — all match.
  - Reproducibility: env locked (uv.lock, .python-version 3.11), central seed threaded,
    config-driven params, CI green, 69 tests pass / 0 skip.
  - Credits: MIT code; CC0 datasets cited with DOIs + ds002778 contact request.
- **Completion standard (Section 31):** met — reproducible, provenance clear,
  participant leakage prevented and tested, internal + external evaluations complete,
  results reported honestly with uncertainty, dataset shift + confounding examined,
  code tested/documented, dashboard communicates without clinical claims.
- **Next step:** owner review + merge; tag `v0.1.0`. Optional future work: deploy
  (GitHub Pages / Heroku), deferred sensitivity analyses, PPMI/harmonization stretch goals.

---

## 2026-07-24 — Deployment (GitHub Pages + Heroku)

- **Goal (owner-approved):** stand up the public interfaces on precomputed,
  de-identified outputs. Owner said "merge and set up deployment too" -> merged PR #10
  (M8), tagged v0.1.0, branched deployment off main.
- **Work completed:** `scripts/build_site.py` generates a self-contained static
  research site (`site/index.html`) from `dashboard/data/` — scientific-instrument
  design (teal = disease signal vs amber = dataset shift, encoding the finding);
  `.github/workflows/pages.yml` deploys `site/` to GitHub Pages. Heroku files for the
  Streamlit dashboard (`Procfile`, `requirements.txt`, `runtime.txt`,
  `.streamlit/config.toml`). `docs/deployment.md`. Added a test that the published site
  is de-identified (no participant ids) and shows the disclaimer. 70 pass / 0 skip;
  ruff format+check + mypy clean.
- **Guardrails:** both interfaces serve only derived, de-identified data; no raw EEG at
  runtime, no upload, no individual prediction; disclaimer prominent.
- **Next step:** owner merges the deployment PR; enable Pages (Settings -> Pages ->
  Source = GitHub Actions) so the site publishes; optionally deploy Heroku (needs owner
  account). Site URL: https://kalebrodriguez.github.io/NeuroPD/.

---

## 2026-07-24 — Sensitivity analyses + multi-page site (owner-requested)

- **Goal:** owner asked for (a) the deferred sensitivity analyses, (b) a fuller
  multi-page deployed site, (c) expanded site content — prompted by fair skepticism
  that a one-day build could be valid. Also fixed the live Pages deploy (legacy Jekyll
  builder was overriding the workflow; reset Pages to workflow-only).
- **Work completed:**
  - `extract_features.py --spatial channel`; channel-level matrices extracted.
  - `scripts/sensitivity.py` (+ ADR 0010, `docs/sensitivity.md`): harmonization
    (region vs channel), age/sex adjustment (in-fold residualization, no leakage),
    feature-family contributions.
  - `explain.py` emits `feature_importance.json`; `build_dashboard_data.py` bundles
    sensitivity + importance; `build_site.py` rewritten as a 7-page static site
    (overview, datasets, biomarkers with pre-rendered SVG box plots, results,
    dataset-shift, sensitivity, methods) with shared nav. Test covers all pages.
- **Results (executed, confirmatory/exploratory; external n=30 = directional):**
  - **Harmonization:** region external AUC 0.671 vs channel 0.529 (chance) — region
    aggregation validated.
  - **Age/sex:** EEG residualized on age/sex still AUC 0.668 (>chance) — EEG has signal
    independent of demographics, though demographics remains a strong confound.
  - **Feature family:** relative power external AUC **0.867** vs absolute 0.591 / log
    0.640 / slowing 0.476 / complexity 0.493 — normalized features transfer, scale-
    sensitive ones don't.
- **Interpretation update:** the honest headline sharpens from "biomarkers don't
  transfer" to "**modest, normalization-dependent transfer**": relative band power
  transfers meaningfully; the full feature set dilutes it with non-transferable
  absolute/log/slowing/complexity features. Still not conclusive at n=30.
- **Next step:** owner review; stretch goals (third cohort, ComBat harmonization) would
  make the relative-power transfer result confirmable.
