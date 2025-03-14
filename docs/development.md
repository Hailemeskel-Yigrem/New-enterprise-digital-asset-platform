# Development Guide

## Prerequisites

- Python 3.12+
- Poetry 1.8+
- Docker Desktop
- Node.js 20+ (for the web console)

## Local setup

`ash
cp .env.example .env
poetry install
docker compose up -d
poetry run uvicorn vaultforge.main:app --reload
`

## Quality checks

`ash
make lint
make typecheck
make test
`
