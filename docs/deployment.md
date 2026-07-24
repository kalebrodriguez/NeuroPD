# Deployment

Two public interfaces, both serving **only** precomputed, de-identified outputs.
Neither accepts EEG uploads, requires raw data at runtime, or makes individual
diagnostic predictions (spec Section 17 + deployment roadmap).

## 1. GitHub Pages — static research site (primary)

A single self-contained page (`site/index.html`) generated from
`dashboard/data/` by `scripts/build_site.py`. No server, no runtime dependencies.

**Regenerate after re-running the analysis:**

```bash
uv run python scripts/build_dashboard_data.py   # refresh dashboard/data/
uv run python scripts/build_site.py             # rewrite site/index.html
```

**Deploy:** the `.github/workflows/pages.yml` workflow publishes `site/` on every
push to `main` that touches it (or via *Actions → Deploy GitHub Pages → Run
workflow*). One-time repository setup: **Settings → Pages → Build and deployment →
Source = GitHub Actions**. The live URL is
`https://kalebrodriguez.github.io/NeuroPD/`.

## 2. Heroku — interactive Streamlit dashboard (optional)

The richer, interactive dashboard (`dashboard/app.py`). Files provided:

- `Procfile` — starts Streamlit on Heroku's `$PORT`, headless.
- `requirements.txt` — the dashboard's runtime deps only (streamlit, plotly,
  pandas); it does **not** import the analysis package. Local dev/CI still use
  `uv` + `pyproject.toml`.
- `runtime.txt` — Python 3.11.
- `.streamlit/config.toml` — headless server config.

**Deploy (requires your Heroku account; the GitHub Student Pack includes credit):**

```bash
heroku create neuropd-dashboard
git push heroku deployment-pages-heroku:main   # or main, once merged
heroku open
```

Heroku is optional; GitHub Pages is the canonical public interface. Do not deploy
either until the analysis is final (it is, as of v0.1.0). Neither surface exposes
raw EEG or participant identifiers.
