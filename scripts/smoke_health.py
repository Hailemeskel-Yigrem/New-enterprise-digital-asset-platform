"""Simple health endpoint smoke check."""

from __future__ import annotations

import os
import sys

import httpx


def main() -> int:
    base = os.environ.get("VAULTFORGE_BASE_URL", "http://localhost:8000")
    with httpx.Client(timeout=5.0) as client:
        response = client.get(f"{base}/health")
        response.raise_for_status()
        payload = response.json()
        print(payload)
        return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
