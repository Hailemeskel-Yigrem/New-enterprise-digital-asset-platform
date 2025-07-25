#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> ruff"
poetry run ruff check src tests

echo "==> black"
poetry run black --check src tests

echo "==> mypy"
poetry run mypy src

echo "==> pytest"
poetry run pytest -q

echo "All checks passed."
