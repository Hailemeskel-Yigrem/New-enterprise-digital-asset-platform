#!/usr/bin/env python3
"""Re-materialize expansion files with UTF-8 encoding and LF newlines."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    "README.md",
    "CHANGELOG.md",
    "docs/setup.md",
    "docs/development.md",
    "docs/deployment.md",
    "docs/api.md",
    "docs/troubleshooting.md",
    "alembic/versions/20250420_0002_assets_tables.py",
    "alembic/versions/20250510_0003_workflows_signatures.py",
    "alembic/versions/20250520_0004_audit_collaboration.py",
    "alembic/versions/20250601_0005_settings.py",
    "scripts/dev_bootstrap.sh",
    "scripts/dev_bootstrap.ps1",
    "scripts/run_checks.sh",
    "scripts/seed_demo_data.py",
    "src/vaultforge/core/pagination.py",
    "src/vaultforge/api/middleware/__init__.py",
    "src/vaultforge/api/middleware/request_id.py",
    "src/vaultforge/api/middleware/timing.py",
    "src/vaultforge/application/assets/document_service.py",
    "src/vaultforge/application/assets/schemas.py",
    "src/vaultforge/main.py",
    "tests/unit/test_auth_service.py",
    "tests/unit/test_organization_service.py",
    "tests/unit/test_document_service_rules.py",
    "tests/unit/test_permission_matrix_complete.py",
    "tests/integration/test_api_auth_flow.py",
    "tests/e2e/test_health_openapi.py",
]


def main() -> None:
    total_lines = 0
    for rel in TARGETS:
        path = ROOT / rel
        if not path.is_file():
            print("SKIP missing:", rel)
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(text, encoding="utf-8", newline="\n")
        lines = len(text.splitlines())
        total_lines += lines
        print(f"  {rel}: {lines}")
    print(f"Materialized {len(TARGETS)} paths (~{total_lines} LOC)")


if __name__ == "__main__":
    main()
