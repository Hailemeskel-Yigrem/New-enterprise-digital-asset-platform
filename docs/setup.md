# Setup Guide

This guide covers local development setup and Docker-based infrastructure for VaultForge.

## Prerequisites

- Python 3.12+
- Poetry 1.8+
- Docker Desktop or Docker Engine + Compose v2
- Git

Optional: Node.js 20+ if working on the `web/` frontend.

## Local setup (recommended)

### 1. Environment

```bash
cp .env.example .env
```

Edit `.env` and set strong values for `APP_SECRET_KEY` and `JWT_SECRET_KEY` (minimum 16 characters each).

### 2. Bootstrap script

**Linux / macOS:**

```bash
chmod +x scripts/dev_bootstrap.sh scripts/run_checks.sh
./scripts/dev_bootstrap.sh
```

**Windows (PowerShell):**

```powershell
.\scripts\dev_bootstrap.ps1
```

The bootstrap script:

1. Copies `.env.example` to `.env` if missing
2. Runs `poetry install`
3. Starts Postgres, Redis, and RabbitMQ via Docker Compose
4. Waits for Postgres readiness
5. Applies Alembic migrations (`alembic upgrade head`)

### 3. Run the API

```bash
poetry run vaultforge
# or
poetry run uvicorn vaultforge.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify

```bash
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

### 5. Demo data (optional)

```bash
poetry run python scripts/seed_demo_data.py --dry-run
poetry run python scripts/seed_demo_data.py
```

Demo credentials: `owner@acme-demo.test` / `DemoPass123!`

## Docker Compose (full stack)

Start all services including API, worker, beat, and Nginx:

```bash
docker compose up -d --build
```

| Service | Port | Purpose |
|---------|------|---------|
| postgres | 5432 | Primary database |
| redis | 6379 | Cache + Celery results |
| rabbitmq | 5672, 15672 | Message broker (+ management UI) |
| api | 8000 | FastAPI application |
| worker | - | Celery worker |
| beat | - | Celery scheduler |
| nginx | 80 | Reverse proxy |

Run migrations inside the API container:

```bash
docker compose exec api alembic upgrade head
```

## Database migrations

```bash
# Apply all migrations
poetry run alembic upgrade head

# Create new migration (after model changes)
poetry run alembic revision --autogenerate -m "describe change"

# Roll back one revision
poetry run alembic downgrade -1
```

Migration chain:

1. `20250315_0001` - identity (organizations, users, memberships, teams)
2. `20250420_0002` - assets (folders, documents, versions, locks)
3. `20250510_0003` - workflows and signatures
4. `20250520_0004` - audit and collaboration
5. `20250601_0005` - organization settings

## Storage

Local development stores uploaded files under `./storage` (configurable via `STORAGE_LOCAL_PATH`). The directory is created automatically on first upload.

## Running quality checks

```bash
./scripts/run_checks.sh
```

Runs Ruff, Black, MyPy, and Pytest in sequence.

## IDE tips

- Set `PYTHONPATH=src` or open the repo root in your IDE so imports resolve to `vaultforge.*`
- Use the `.env` file for local overrides; never commit secrets
- Enable format-on-save with Black (line length 100)
