# ADR 0003: Environment manager (uv) and Python 3.11

- **Date:** 2026-07-23
- **Status:** accepted

## Context
The target VM shipped with system Python 3.12 and no environment manager. The
specification prefers `uv` and Python 3.11 (spec Section 7, Section 9), and the
owner approved resolving this during Milestone 0.

## Decision
Use **`uv`** as the environment manager and **pin Python 3.11** via
`.python-version`, with a committed `uv.lock` for reproducible installs. No
GPU-only dependencies are added (CPU-only scope; no deep learning initially).

## Alternatives
- Use system Python 3.12 with `pip`/`venv` (rejected: less reproducible locking and
  diverges from the spec's preferred, well-supported toolchain).

## Scientific justification
Locked environments and a pinned interpreter make numerical results reproducible on
a clean machine — a core requirement of the project.

## Consequences
Contributors and CI must install `uv`. Python is constrained to `>=3.11,<3.12`;
dependency upgrades are mediated through `uv.lock`.
