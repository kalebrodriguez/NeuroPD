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
