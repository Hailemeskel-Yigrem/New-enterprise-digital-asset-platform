# Changelog

All notable changes to VaultForge are documented here. Versioning follows Semantic Versioning.

## [0.8.0] - 2025-07-01

### Added
- Request ID and timing middleware (`X-Request-ID`, `X-Response-Time-Ms`)
- Pagination helpers (`Page`, `PageParams`) in `core/pagination.py`
- Document service: metadata update, archive, version listing, content download
- Production documentation (setup, deployment, API reference, troubleshooting)
- Bootstrap scripts (`dev_bootstrap.sh`, `dev_bootstrap.ps1`, `run_checks.sh`)
- Demo data seed script with `--dry-run`
- Expanded test suite: auth, organization, document rules, permission matrix, API auth flow, e2e OpenAPI

### Changed
- README rewritten with architecture diagram and feature list
- Alembic migration chain completed through organization settings

## [0.7.0] - 2025-06-15

### Added
- Organization settings module (default sensitivity, upload limits, retention)
- Settings API and admin endpoints
- Settings persistence model and service tests

### Changed
- Organization update supports plan and storage quota fields

## [0.6.0] - 2025-06-01

### Added
- Collaboration: comments, @mentions, in-app notifications
- WebSocket notification channel per organization
- Connection manager for live push
- Mention parsing and notification dispatch

### Fixed
- Comment thread parent_id validation

## [0.5.0] - 2025-05-20

### Added
- Immutable audit event log with JSON metadata
- Activity feed for user-facing timelines
- Audit and activity API routes
- Audit service with actor/resource indexing

## [0.4.0] - 2025-05-10

### Added
- Approval workflow definitions (steps, assignees)
- Workflow instances with step-by-step progression
- Digital signature requests and multi-signer support
- Signature hash verification utilities

### Changed
- Document status transitions coordinated with workflow completion

## [0.3.0] - 2025-04-20

### Added
- Folder hierarchy with move/rename rules
- Document upload, versioning, checkout/checkin locks
- Local filesystem storage backend
- Document search service
- SHA-256 checksums on every version

### Fixed
- Circular FK between documents and document_versions (deferred constraint)

## [0.2.0] - 2025-03-25

### Added
- Team management within organizations
- RBAC permission matrix (6 roles, 16 permissions)
- JWT access and refresh token flow
- Organization CRUD and member invitation
- FastAPI dependency injection layer

### Changed
- API error responses standardized to `{code, message}`

## [0.1.0] - 2025-03-15

### Added
- Initial project scaffolding (Poetry, Docker Compose, Nginx)
- FastAPI application shell with health endpoints
- Identity domain: organizations, users, memberships
- Alembic initial migration for identity tables
- SQLAlchemy async session setup
- Pytest, Ruff, Black, MyPy configuration
