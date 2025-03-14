PYTHON ?= python
POETRY ?= poetry

.PHONY: install lint format typecheck test run docker-up docker-down migrate

install:
	$(POETRY) install

lint:
	$(POETRY) run ruff check src tests
	$(POETRY) run black --check src tests

format:
	$(POETRY) run ruff check --fix src tests
	$(POETRY) run black src tests

typecheck:
	$(POETRY) run mypy src

test:
	$(POETRY) run pytest -q

run:
	$(POETRY) run uvicorn vaultforge.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker compose up -d

docker-down:
	docker compose down

migrate:
	$(POETRY) run alembic upgrade head