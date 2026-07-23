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
