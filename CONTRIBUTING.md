# Contributing to NeuroPD

NeuroPD is a research-grade, reproducibility-focused project. Contributions and
review should preserve scientific rigor and participant privacy.

## Development setup

```bash
# Requires uv (https://docs.astral.sh/uv/). Python 3.11 is provisioned by uv.
make install      # uv sync --extra dev
make check        # ruff lint + mypy + pytest
```

Common tasks are exposed through the `Makefile` (`make lint`, `make test`,
`make smoke`, `make format`, `make typecheck`).

## Ground rules

- **Never commit data or secrets.** Raw and derived EEG, `.env` files, and any
  identifiable or controlled-access information must never be committed. The
  `.gitignore` enforces this; do not weaken it.
- **Keep raw data immutable.** Raw datasets live under `data/raw/` and are never
  modified in place.
- **Participant isolation is non-negotiable.** All recordings/sessions from one
  participant must stay within a single split. Changes touching splitting logic
  must keep `tests/test_splits.py` green.
- **No fabricated results or citations.** Every reported number must come from
  executed code; every citation must be verifiable (DOI/PubMed/publisher).
- **Configuration over hard-coding.** Scientifically meaningful parameters belong
  in `configs/`, not scattered in code, and must be justified after inspecting
  real data (see decision records under `docs/decisions/`).
- **No clinical claims.** This is a research tool, not a diagnostic device. Use
  the approved language in the specification (Section 6.5).

## Pull requests

- Keep commits small and coherent.
- Ensure `make check` passes and CI is green (CI never downloads full datasets).
- Update `docs/research_log.md` and `CHANGELOG.md` as appropriate.
- For methodological changes, add or update a decision record in
  `docs/decisions/`.
