# Release Checklist

1. Update `CHANGELOG.md` and package version
2. Run `scripts/run_checks.sh` (or `poetry run pytest`)
3. Build images: `docker compose build`
4. Apply migrations on a staging database
5. Smoke test `/health`, `/ready`, `/docs`, and login
6. Tag release and publish notes
