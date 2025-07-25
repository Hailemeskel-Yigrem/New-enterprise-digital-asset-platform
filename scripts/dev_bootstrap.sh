#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

if command -v poetry >/dev/null 2>&1; then
  poetry install --no-interaction
else
  echo "Poetry not found; install from https://python-poetry.org/" >&2
  exit 1
fi

docker compose up -d postgres redis rabbitmq
echo "Waiting for postgres..."
until docker compose exec -T postgres pg_isready -U vaultforge >/dev/null 2>&1; do sleep 1; done

poetry run alembic upgrade head
echo "VaultForge dev bootstrap complete. Run: poetry run vaultforge"
