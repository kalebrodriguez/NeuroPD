.PHONY: help install lint format typecheck test smoke check clean

help:
	@echo "NeuroPD make targets:"
	@echo "  install    Create/sync the uv environment (dev extras)"
	@echo "  lint       Run ruff lint checks"
	@echo "  format     Apply ruff formatting"
	@echo "  typecheck  Run mypy on the package"
	@echo "  test       Run the pytest suite"
	@echo "  smoke      Run the fast smoke tests (no data download)"
	@echo "  check      Run lint + typecheck + test"
	@echo "  clean      Remove caches and build artifacts"

install:
	uv sync --extra dev

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy

test:
	uv run pytest

smoke:
	uv run pytest tests/test_smoke_pipeline.py tests/test_splits.py

check: lint typecheck test

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info \
		src/*.egg-info .coverage coverage.xml htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
