# Security Policy

## Supported versions

| Version   | Supported |
|-----------|-----------|
| 1.0.x     | Yes       |
| 0.9.x     | Yes       |
| 1.0.0-rc1 | Yes       |
| < 0.9     | No        |

## Reporting a vulnerability

Do **not** open public issues for security bugs. Email **hailemeskelyigrem5@gmail.com** with:

- A description of the issue and affected endpoints
- Steps to reproduce
- Affected versions and suggested fix (if known)

We aim to acknowledge reports within 72 hours.

## Practices

- Rotate `APP_SECRET_KEY` and `JWT_SECRET_KEY` on deploy boundaries.
- Never commit `.env` or OAuth client secrets.
- Enable rate limiting in production (`RATE_LIMIT_ENABLED=true`).
- Keep PostgreSQL, Redis, and RabbitMQ off public networks.
- Restrict OAuth redirect URIs to known application origins.

See [docs/security.md](docs/security.md) for JWT, RBAC, and secrets handling.
