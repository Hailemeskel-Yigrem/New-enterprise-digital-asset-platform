# VaultForge Operations Runbook

## Deploy / upgrade

```bash
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build
docker compose exec api alembic upgrade head
```

Verify after deploy:

```bash
curl -sf http://localhost/health
curl -sf "http://localhost/ready?check_deps=true"
curl -sf http://localhost/metrics | head
```

## Runbook: Celery worker failures

### Symptoms

- Background jobs stuck in `pending` state
- Export/import tasks never complete
- RabbitMQ queue depth growing
- No recent entries in worker logs

### Diagnosis

```bash
docker compose ps worker
docker compose logs --tail=200 worker
docker compose exec worker celery -A vaultforge.infrastructure.messaging.celery_app.celery_app inspect ping
docker compose exec worker celery -A vaultforge.infrastructure.messaging.celery_app.celery_app inspect active
```

Check Redis result backend connectivity and RabbitMQ management UI (`:15672` in dev only).

### Remediation

1. Restart workers: `docker compose restart worker`
2. If OOM killed, increase memory limits in `deploy/docker-compose.prod.yml`
3. Scale replicas if queue depth remains high
4. Re-queue failed jobs from admin API or mark as failed with audit note
5. If broker corrupted, drain queue after backup and restart RabbitMQ

### Prevention

- Alert on queue depth > threshold for 5 minutes
- Monitor worker memory and restart policy (`unless-stopped`)

## Runbook: Disk full

### Symptoms

- Document upload returns 500
- Logs contain `No space left on device`
- PostgreSQL or storage volume at 100%

### Diagnosis

```bash
df -h
du -sh storage/* | sort -h | tail -20
docker system df
```

Check for orphaned export ZIP files, failed upload temp files, and audit log growth.

### Remediation

1. Purge completed export artifacts older than retention window
2. Run retention enforcement job (respecting legal holds)
3. Expand Docker volume or attach larger block storage
4. Rotate application logs (`max-size` / `max-file` in prod compose)
5. Notify affected organizations if uploads were rejected

### Prevention

- Alert at 80% and 90% disk utilization
- Scheduled retention policy execution via Celery beat

## Runbook: Migration rollback

### Before any migration

1. Put API behind maintenance page or scale to zero
2. Stop workers and beat: `docker compose stop worker beat`
3. Record current revision: `docker compose exec api alembic current`
4. Take PostgreSQL backup: `pg_dump -Fc vaultforge > backup_$(date +%F).dump`

### Rollback procedure

**Option A — Alembic downgrade (reversible migrations only)**

```bash
docker compose exec api alembic downgrade -1
# redeploy previous application image tag
docker compose up -d api worker beat
```

**Option B — Restore from backup (destructive data loss since backup)**

```bash
docker compose stop api worker beat
# restore dump into postgres volume
docker compose start api
docker compose exec api alembic current  # verify matches restored schema
```

Never downgrade without a verified backup. Forward-fix is preferred when downgrade drops columns.

### Post-rollback verification

- `alembic current` matches expected revision
- `/ready?check_deps=true` returns `ready`
- Smoke test login and document read

## Monitoring

Prometheus scrapes `/metrics` per `deploy/prometheus/prometheus.yml`.

Recommended alerts:

| Signal | Threshold | Action |
|--------|-----------|--------|
| HTTP 5xx rate | > 1% for 5m | Check API logs, DB connectivity |
| `/ready` degraded | any dependency error | Failover or restart dependency |
| Request p99 latency | > 2s for 10m | Scale API, check slow queries |
| Celery queue depth | > 1000 for 5m | Scale workers |
| Disk usage | > 90% | Run disk full runbook |

## Log correlation

Use `X-Request-ID` from client responses to grep structured logs.
Request context vars (`core/context.py`) propagate org and user IDs when set by middleware.
