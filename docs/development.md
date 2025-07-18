# Development Guide

Guidelines for contributing to VaultForge and extending the platform.

## Architecture layers

VaultForge follows a layered (hexagonal) architecture:

```
┌─────────────────────────────────────────┐
│  api/          HTTP, WebSocket, DTOs    │
├─────────────────────────────────────────┤
│  application/  Use cases, orchestration │
├─────────────────────────────────────────┤
│  domain/       Entities, enums, ports   │
├─────────────────────────────────────────┤
│  infrastructure/ Adapters (DB, cache)   │
└─────────────────────────────────────────┘
```

**Rules:**

- `domain/` must not import from `application/`, `api/`, or `infrastructure/`
- `application/` depends on domain interfaces, not SQLAlchemy models
- `infrastructure/` implements domain repository protocols
- `api/` wires FastAPI routes to application services via `api/deps.py`

## Coding standards

| Tool | Purpose | Config |
|------|---------|--------|
| Black | Formatting | `pyproject.toml`, line-length 100 |
| Ruff | Lint + import sort | `select = E,F,I,N,UP,B,SIM,ASYNC` |
| MyPy | Static typing | `strict = true` on `vaultforge` package |
| Pytest | Tests | `asyncio_mode = auto` |

### Conventions

- Use `StrEnum` for domain enumerations
- Dataclasses with `slots=True` for entities
- Async SQLAlchemy sessions via `get_db_session()`
- Raise domain exceptions (`NotFoundError`, `ConflictError`, etc.) from services; map to HTTP in API layer
- UUID primary keys everywhere
- Timestamps: timezone-aware UTC (`TimestampMixin`)

### Naming

- Models: `FooModel` in `infrastructure/persistence/models/`
- Entities: `Foo` in `domain/*/entities.py`
- Services: `FooService` in `application/*/`
- Repositories: `FooRepository` (protocol) + `SqlAlchemyFooRepository` (adapter)

## How to add a module

Example: adding a **retention policy** feature.

### 1. Domain

```
src/vaultforge/domain/retention/
  __init__.py
  entities.py      # RetentionPolicy dataclass
  enums.py         # PolicyScope, PolicyAction
  repositories.py  # RetentionPolicyRepository ABC
```

### 2. Infrastructure

```
src/vaultforge/infrastructure/persistence/models/retention.py
src/vaultforge/infrastructure/persistence/repositories/retention_repository.py
```

Add Alembic migration under `alembic/versions/`.

### 3. Application

```
src/vaultforge/application/retention/
  __init__.py
  schemas.py       # Pydantic request/response models
  retention_service.py
```

### 4. API

```
src/vaultforge/api/v1/retention.py
```

Register router in `api/v1/router.py`:

```python
from vaultforge.api.v1 import retention
api_v1_router.include_router(retention.router)
```

Add dependency factory in `api/deps.py` if needed.

### 5. Permissions

Add new `Permission` enum values and map them in `ROLE_PERMISSIONS` (`domain/identity/enums.py`).

Use `require_permission(Permission.YOUR_PERM)` on routes.

### 6. Tests

```
tests/unit/test_retention_service.py
tests/integration/test_api_retention.py
```

Run `./scripts/run_checks.sh` before opening a PR.

## Middleware

- `RequestIdMiddleware` - propagates `X-Request-ID`
- `TimingMiddleware` - adds `X-Response-Time-Ms`, logs requests >= 1s

Registered in `main.py` (timing outermost, request ID inner).

## Pagination

Use `PageParams` and `Page[T]` from `core/pagination.py` for list endpoints:

```python
from vaultforge.core.pagination import Page, PageParams

params = PageParams(page=1, page_size=50)
return Page.build(items, total=total_count, params=params)
```

## Background tasks

Celery app: `vaultforge.infrastructure.messaging.celery_app`

Define tasks in `infrastructure/messaging/tasks.py`. Workers consume from RabbitMQ; results stored in Redis.

## Logging

Structured logging via `structlog`. Use:

```python
from vaultforge.core.logging import get_logger
log = get_logger(__name__)
log.info("event_name", key=value)
```

## Common workflows

| Task | Command |
|------|---------|
| New migration | `poetry run alembic revision -m "..."` |
| Run single test | `poetry run pytest tests/unit/test_foo.py -v` |
| Type check one file | `poetry run mypy src/vaultforge/path/to/file.py` |
| Format | `poetry run black src tests` |
