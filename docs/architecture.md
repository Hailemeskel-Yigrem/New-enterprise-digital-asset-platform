# VaultForge Architecture

VaultForge follows **Domain-Driven Design (DDD)** with a strict layered architecture.
Dependencies point inward: **API -> Application -> Domain <- Infrastructure**.

## Layer overview

| Layer | Location | Responsibility | May depend on |
|-------|----------|----------------|---------------|
| **API** | `src/vaultforge/api/` | HTTP routes, middleware, WebSocket, DI wiring | Application, Core |
| **Application** | `src/vaultforge/application/` | Use-case services, DTOs, orchestration | Domain, Core |
| **Domain** | `src/vaultforge/domain/` | Entities, value objects, enums, repository ports | Core (exceptions only) |
| **Infrastructure** | `src/vaultforge/infrastructure/` | SQLAlchemy, Redis, Celery, storage, OAuth | Domain, Core |
| **Core** | `src/vaultforge/core/` | Config, logging, pagination, context, telemetry | stdlib / pydantic only |

The **Domain** layer has no knowledge of FastAPI, SQLAlchemy, or Redis. Repository interfaces
(`protocol`/`ABC` in `domain/*/repositories.py`) define persistence contracts; concrete
implementations live under `infrastructure/persistence/repositories/`.

## API layer

- **Routers** (`api/v1/*.py`) translate HTTP to application service calls.
- **Dependencies** (`api/deps.py`) resolve DB sessions, current user, and permission checks.
- **Middleware** assigns request IDs, timing headers, CORS, and rate limits.
- **Error mapping** converts `VaultForgeError` subclasses to `{code, message}` JSON responses.

Routes must remain thin: validate input, authorize, delegate, map errors.

## Application layer

Application services are `@dataclass` orchestrators that:

1. Accept Pydantic DTOs from the API.
2. Load aggregates through repository interfaces.
3. Invoke domain entity methods and enforce invariants.
4. Persist changes and return response DTOs.
5. Raise typed `VaultForgeError` on rule violations.

Each bounded context has its own package (`application/identity/`, `application/documents/`, etc.).

## Domain layer

Bounded contexts and their aggregates:

| Context | Aggregates | Key invariants |
|---------|------------|----------------|
| **Identity** | User, Organization, Membership, Team | RBAC via role->permission matrix; active membership required |
| **Documents** | Folder, Document, DocumentVersion | Org scoping; version immutability; checkout locks |
| **Workflows** | WorkflowDefinition, WorkflowInstance | Step progression; assignee validation |
| **Signatures** | SignatureRequest | Multi-signer ordering; hash verification |
| **Audit** | AuditEvent | Append-only; actor/resource indexing |
| **Sharing** | ShareLink, ShareACL | Token expiry; permission scopes |
| **Retention** | RetentionPolicy, LegalHold | Policy precedence; hold blocks purge |

Entities inherit timestamps from `domain/common.py`. Business logic belongs on entities, not services,
when the rule is intrinsic to a single aggregate.

## Infrastructure layer

| Concern | Package |
|---------|---------|
| Persistence | `infrastructure/persistence/` (models, repositories, session) |
| Security | `infrastructure/security/` (JWT, bcrypt, OAuth) |
| Messaging | `infrastructure/messaging/` (Celery app, tasks) |
| Storage | `infrastructure/storage/` (local filesystem backend) |
| Cache | `infrastructure/cache/` (Redis client) |
| Search | `infrastructure/search/` (indexer, query builder) |

Alembic migrations under `alembic/versions/` evolve the relational schema.

## Core cross-cutting concerns

| Module | Purpose |
|--------|---------|
| `core/config.py` | Pydantic settings from environment |
| `core/logging.py` | Structlog configuration |
| `core/pagination.py` | `PageParams` / `Page` envelopes |
| `core/context.py` | Request-scoped `ContextVar` for org/user/request ID |
| `core/telemetry.py` | Timing helpers and Prometheus counter integration |
| `core/exceptions.py` | Shared error hierarchy |

## Request flow (document upload)

```
Client -> Nginx -> FastAPI middleware chain
  -> require_permission(DOCUMENT_UPLOAD)
  -> DocumentService.upload()
  -> StorageBackend.write() + DocumentRepository.add()
  -> Celery task: search index + audit event
  -> JSON response
```

## Multi-tenancy

Every resource is scoped by `organization_id`. The API resolves the active org from the URL path
(`/organizations/{org_id}/...`) and validates membership before executing use cases.
Roles map to permissions via `ROLE_PERMISSIONS` in `domain/identity/enums.py`.

## Observability

- Structured logging via `core/logging.py`
- Request ID propagation (`X-Request-ID`) and timing (`X-Response-Time-Ms`)
- Prometheus text metrics at `/metrics` (see `core/telemetry.py`, `api/monitoring.py`)
- Dependency probes at `/health/deps` and `/ready?check_deps=true`
- Production Prometheus scrape config in `deploy/prometheus/prometheus.yml`

## Deployment topology

```
                    +---------+
                    |  Nginx  |
                    +----+----+
                         |
              +----------+----------+
              |     API (x2)        |
              +----------+----------+
         +-----+----------+----------+-----+
         |                |                |
    +----v----+     +-----v-----+    +-----v-----+
    | Postgres|     |   Redis   |    | RabbitMQ  |
    +---------+     +-----------+    +-----+-----+
                                           |
                              +------------+------------+
                              | Worker (x2) + Beat      |
                              +-------------------------+
```
