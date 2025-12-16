# VaultForge Security Model

## Authentication (JWT)

| Token | TTL (default) | Claims |
|-------|---------------|--------|
| Access | 30 minutes (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`) | `sub` (user UUID), `type=access`, `exp`, `iat` |
| Refresh | 14 days (`JWT_REFRESH_TOKEN_EXPIRE_DAYS`) | `sub`, `type=refresh`, `exp`, `iat` |

Tokens are signed with `JWT_SECRET_KEY` using `JWT_ALGORITHM` (HS256 by default).
Clients send `Authorization: Bearer <access_token>` on protected routes.

### Flows

| Flow | Endpoint | Notes |
|------|----------|-------|
| Register | `POST /api/v1/auth/register` | Creates user; bcrypt password hash |
| Login | `POST /api/v1/auth/login` | Returns access + refresh pair |
| Refresh | `POST /api/v1/auth/refresh` | Rotates token pair; validates refresh type |
| Current user | `GET /api/v1/auth/me` | Requires valid access token |
| OAuth/OIDC | `/api/v1/oauth/*` | Optional; configure via `OAUTH_*` env vars |

Refresh tokens must never be stored in browser localStorage in production SPAs; prefer
httpOnly cookies or secure native storage.

## Authorization (RBAC)

Organization-scoped roles:

| Role | Typical use |
|------|-------------|
| `owner` | Full org control including billing settings |
| `admin` | User/team management, settings |
| `manager` | Content and workflow administration |
| `contributor` | Upload and edit documents |
| `viewer` | Read-only access |
| `auditor` | Audit and report read access |

Permissions (e.g. `document:upload`, `user:manage`) are defined in `domain/identity/enums.py`
and checked via `require_permission()` in `api/deps.py`. Only **active** memberships grant access;
`invited`, `suspended`, and `removed` statuses are rejected.

### Enforcement points

1. **Route dependency** — `require_permission(Permission.X)` loads membership and checks role matrix.
2. **Application service** — validates org ownership of resources before mutation.
3. **Domain entity** — enforces aggregate invariants (e.g. signer must be on signature request).

## Request context

`core/context.py` exposes `ContextVar` accessors for `org_id`, `user_id`, and `request_id`.
Middleware and dependencies may populate these for structured logging and audit correlation.

## Secrets management

| Variable | Purpose | Rotation |
|----------|---------|----------|
| `APP_SECRET_KEY` | App-level signing (sessions, CSRF if enabled) | Every major release |
| `JWT_SECRET_KEY` | JWT signing | Invalidates all tokens when rotated |
| `DATABASE_URL` | PostgreSQL credentials | Via DBA / secret manager |
| `OAUTH_DEFAULT_CLIENT_SECRET` | Built-in OAuth client | On compromise |
| `OAUTH_GOOGLE_CLIENT_SECRET` | Google OIDC | Per Google Cloud console |

**Never commit secrets.** Use environment injection, Docker secrets, or a vault (HashiCorp Vault,
AWS Secrets Manager, Azure Key Vault) in production.

## Rate limiting

Configured via `RATE_LIMIT_*` environment variables (see `.env.example`).
Redis-backed sliding window in `api/middleware/rate_limit.py` protects auth, OAuth, and export endpoints.

## Production checklist

- [ ] `APP_ENV=production`, `APP_DEBUG=false`
- [ ] TLS termination at reverse proxy (Nginx)
- [ ] Strong random secrets (>= 32 characters)
- [ ] Rate limiting enabled
- [ ] Database and Redis not publicly exposed
- [ ] OAuth redirect URIs restricted to known origins
- [ ] Structured logs shipped to central aggregation
- [ ] Prometheus alerts on 5xx rate and dependency health
