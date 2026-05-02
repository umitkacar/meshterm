# meshterm — local development Makefile
#
# Targets:
#   make help        - this listing
#   make install     - install dev dependencies (uv-based)
#   make test        - run pytest
#   make lint        - run ruff check
#   make typecheck   - run mypy strict
#   make build       - build wheel + sdist via uv build
#   make clean       - remove dist/ build/ caches
#   make publish-test - upload current dist/ to TestPyPI (requires twine + .pypirc)
#   make smoketest   - import + version + CLI smoke (requires built wheel)

.PHONY: help install test lint typecheck build clean publish-test smoketest

PKG := meshterm
WHEEL := dist/$(shell ls dist/ 2>/dev/null | grep -E '^meshterm-.*\.whl$$' | head -1)

help:
	@grep -E '^[a-zA-Z_-]+:.*?# ' $(MAKEFILE_LIST) || awk '/^[a-z][a-zA-Z_-]*:/{print}' $(MAKEFILE_LIST)

install:
	uv venv .venv --python 3.11
	. .venv/bin/activate && uv pip install -e ".[dev]"

test:
	uv run pytest tests/ -q

lint:
	uv run ruff check src/ tests/

typecheck:
	uv run mypy --strict src/$(PKG)

build: clean
	uv build

clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info .pytest_cache .mypy_cache .hypothesis .ruff_cache

publish-test: build
	uv run --with twine twine check dist/*
	uv run --with twine twine upload --repository testpypi dist/*

smoketest:
	@test -n "$(WHEEL)" || (echo "ERROR: no wheel in dist/, run 'make build' first" && exit 1)
	uv venv /tmp/$(PKG)-smoketest --python 3.11
	. /tmp/$(PKG)-smoketest/bin/activate && \
		uv pip install $(WHEEL) && \
		python -c "import $(PKG); print(f'$(PKG) version: {$(PKG).__version__}')" && \
		meshterm --version
	rm -rf /tmp/$(PKG)-smoketest
