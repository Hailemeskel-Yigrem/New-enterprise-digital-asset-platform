# Troubleshooting

Common issues when developing or deploying VaultForge.

## Installation & bootstrap

### Poetry not found

```
Poetry not found; install from https://python-poetry.org/
```

Install Poetry and ensure it is on your `PATH`. Re-run `./scripts/dev_bootstrap.sh`.

### `APP_SECRET_KEY` / `JWT_SECRET_KEY` validation error

Pydantic requires both secrets with minimum length 16. Update `.env`:

```
APP_SECRET_KEY=your-long-random-production-secret
JWT_SECRET_KEY=another-long-random-jwt-secret
```

### Docker Compose services fail to start

```bash
docker compose ps
docker compose logs postgres
```

Common causes:

- Port 5432/6379/5672 already in use - stop local Postgres/Redis or change mapped ports
- Insufficient Docker memory - allocate at least 4 GB to Docker Desktop

## Database

### `alembic upgrade head` fails with connection refused

Postgres is not ready. Wait and retry:

```bash
docker compose exec postgres pg_isready -U vaultforge
poetry run alembic upgrade head
```

Ensure `DATABASE_URL` matches Compose credentials:

```
postgresql+asyncpg://vaultforge:vaultforge@localhost:5432/vaultforge
```

### Migration revision conflict

```
Can't locate revision identified by '...'
```

Ensure all migration files are present and `down_revision` chain is unbroken:

```
20250315_0001 -> 20250420_0002 -> 20250510_0003 -> 20250520_0004 -> 20250601_0005
```

### `relation "documents" does not exist`

Migrations not applied. Run `alembic upgrade head`.

## API runtime

### 401 on all authenticated routes

- Confirm `Authorization: Bearer <token>` header is set
- Access token may be expired - call `/auth/refresh`
- Verify `JWT_SECRET_KEY` has not changed since token was issued

### 403 forbidden on organization routes

- User is not an **active** member of the organization
- Role lacks required permission - check RBAC matrix in `domain/identity/enums.py`
- Invited/suspended memberships cannot access protected resources

### 409 conflict on document checkout

Another user holds the checkout lock. Wait for checkin or lock expiry.

### Upload fails / 413 payload too large

- Check `STORAGE_MAX_UPLOAD_MB` and Nginx `client_max_body_size`
- Default limit is 100 MB in both places

### Empty storage / file not found after upload

Verify `STORAGE_LOCAL_PATH` exists and is writable. In Docker, ensure `storage_data` volume is mounted.

## Redis & Celery

### Readiness shows Redis error

```bash
docker compose logs redis
curl http://localhost:8000/ready?check_deps=true
```

Confirm `REDIS_URL=redis://localhost:6379/0` for local dev.

### Celery tasks not executing

```bash
docker compose logs worker
docker compose exec worker celery -A vaultforge.infrastructure.messaging.celery_app.celery_app inspect active
```

Ensure RabbitMQ is healthy and `CELERY_BROKER_URL` is correct.

## Tests

### `ModuleNotFoundError: vaultforge`

Run tests via Poetry from repo root:

```bash
poetry run pytest
```

Or set `PYTHONPATH=src`.

### Async test warnings

Pytest asyncio is configured in `pyproject.toml` (`asyncio_mode = auto`). Use `@pytest.mark.asyncio` for async tests if needed.

## Seed script

### Demo org already exists

```
Demo org 'acme-demo' already exists
```

Idempotent by design. Drop the org manually or use a fresh database.

### Dry run

```bash
poetry run python scripts/seed_demo_data.py --dry-run
```

Prints planned inserts without writing.

## Nginx / proxy

### WebSocket disconnects immediately

Ensure proxy passes upgrade headers (see `deploy/nginx/default.conf` `/ws/` block).

### Wrong client IP in audit logs

Set `X-Forwarded-For` and `X-Real-IP` at the reverse proxy.

## Getting help

1. Check logs: `docker compose logs api worker`
2. Hit `/health/deps` for dependency status
3. Include `X-Request-ID` from failing responses when reporting issues
