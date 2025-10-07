# Simple DX Makefile for ai-architect
.PHONY: help venv install test serve lint ingest sweep freeze export-openapi

help:
	@echo "Targets: venv, install, test, serve, lint, ingest, sweep, freeze, export-openapi"

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
