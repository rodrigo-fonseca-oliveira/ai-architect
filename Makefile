# Simple DX Makefile for ai-architect
.PHONY: help venv install test serve lint ingest sweep freeze export-openapi dev-up dev-down prod-up prod-down logs

help:
	@echo "Targets: venv, install, test, serve, lint, ingest, sweep, freeze, export-openapi, dev-up, dev-down, prod-up, prod-down, logs"

venv:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -U pip setuptools wheel
	. .venv/bin/activate && pip install -e .

install:
	. .venv/bin/activate && pip install -e .

test:
	. .venv/bin/activate && pytest -q

serve:
	. .venv/bin/activate && uvicorn app.main:app --reload

lint:
	. .venv/bin/activate && ruff --version >/dev/null 2>&1 || pip install ruff
	. .venv/bin/activate && ruff check . || true

ingest:
	. .venv/bin/activate && python scripts/ingest_docs.py

sweep:
	. .venv/bin/activate && python scripts/sweep_retention.py

freeze:
	. .venv/bin/activate && pip freeze > requirements.txt

export-openapi:
	. .venv/bin/activate && python scripts/export_openapi.py

# Docker helpers

dev-up:
	docker compose up --build -d

dev-down:
	docker compose down

prod-up:
	docker compose -f docker-compose.yml up --build -d

prod-down:
	docker compose -f docker-compose.yml down

logs:
	docker compose logs -f --tail=200

test-docker:
	docker compose run --rm api /bin/sh -lc ". /opt/venv/bin/activate || true; [ -d /opt/venv ] || python -m venv /opt/venv; . /opt/venv/bin/activate; pip install -e .; pytest -q"
