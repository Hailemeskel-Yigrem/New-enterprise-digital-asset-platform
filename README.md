# VaultForge

Enterprise digital asset and document management for organizations that need secure storage, controlled sharing, and auditable collaboration.

## Status

Early foundation — project scaffolding and core tooling only.

## Stack

- **API:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic
- **Data:** PostgreSQL, Redis
- **Jobs:** Celery, RabbitMQ
- **Ops:** Docker Compose, Nginx
- **Quality:** Pytest, Ruff, Black, MyPy, Poetry

## Quick start

```bash
cp .env.example .env
docker compose up -d
```

See [docs/development.md](docs/development.md) once available.
