# Deployment Guide

Production deployment notes for VaultForge using Docker Compose and Nginx.

## Overview

```
Internet -> Nginx -> API -> PostgreSQL
                    -> Redis
                    -> RabbitMQ -> Celery workers
                    -> Storage volume
```

## Docker Compose production

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
```

| Service | Notes |
|---------|-------|
| api | Stateless; scale behind load balancer |
| worker | Scale with --scale worker=N |
| beat | Single scheduler instance only |
| postgres | Prefer managed RDS/Cloud SQL |
| redis | Prefer managed cache |
| nginx | TLS, body size, WebSocket upgrade |

Volumes: postgres_data, redis_data, rabbitmq_data, storage_data.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| APP_ENV | Yes | production |
| APP_DEBUG | Yes | false |
| APP_SECRET_KEY | Yes | 16+ char random |
| JWT_SECRET_KEY | Yes | JWT signing secret |
| DATABASE_URL | Yes | asyncpg URL |
| REDIS_URL | Yes | redis://host:6379/0 |
| CELERY_BROKER_URL | Yes | AMQP URL |
| CELERY_RESULT_BACKEND | Yes | Redis results URL |
| CORS_ORIGINS | Yes | Allowed frontend origins |
| STORAGE_LOCAL_PATH | No | /app/storage in container |

## Nginx

Configuration: deploy/nginx/default.conf. Set client_max_body_size to match STORAGE_MAX_UPLOAD_MB (default 100m). Proxy /ws/ with Upgrade headers for WebSocket notifications.

## Migrations

Run before each release:

```bash
docker compose exec api alembic upgrade head
```

Chain: 20250315_0001 -> 20250420_0002 -> 20250510_0003 -> 20250520_0004 -> 20250601_0005.

## Workers

```bash
docker compose up -d worker beat
docker compose exec worker celery -A vaultforge.infrastructure.messaging.celery_app.celery_app inspect ping
```

## Health probes

| Endpoint | Use |
|----------|-----|
| GET /health | Liveness |
| GET /ready?check_deps=true | Readiness |
| GET /metrics | Monitoring |

## Rollback

Deploy previous image tag. Restore DB snapshot if migration is not backward compatible.
