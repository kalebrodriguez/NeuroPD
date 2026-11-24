.PHONY: help install lint format format-check typecheck test smoke check reproduce reproduce-raw clean

help:
	@echo "NeuroPD make targets:"
	@echo "  install    Create/sync the uv environment (dev extras)"
	@echo "  lint       Run ruff lint checks"
	@echo "  format     Apply ruff formatting"
	@echo "  format-check  Fail if any file needs ruff formatting (as CI does)"
	@echo "  typecheck  Run mypy on the package"
	@echo "  test       Run the pytest suite"
	@echo "  smoke      Run the fast smoke tests (no data download)"
	@echo "  check      Run lint + format-check + typecheck + test (mirrors CI)"
	@echo "  reproduce  Re-run every analysis from existing features and verify vs committed results"
	@echo "  reproduce-raw  Same, from raw EEG (hours; rewrites git-ignored derived data)"
	@echo "  clean      Remove caches and build artifacts"

install:
	uv sync --extra dev

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy

test:
	uv run pytest

smoke:
	uv run pytest tests/test_smoke_pipeline.py tests/test_splits.py

check: lint format-check typecheck test

reproduce:
	uv run python scripts/reproduce.py

reproduce-raw:
	uv run python scripts/reproduce.py --from raw

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info \
		src/*.egg-info .coverage coverage.xml htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
