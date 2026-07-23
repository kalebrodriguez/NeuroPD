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
