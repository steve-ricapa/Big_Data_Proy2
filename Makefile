.PHONY: help test lint inventory

help:
	@echo "Comandos PowerShell e instalacion: README.md; GCP apply requiere aprobacion."
	@echo "make test | lint | inventory (Docker disponible)."

test:
	uv run pytest -q

lint:
	uv run ruff check src services tests airflow/dags airflow/tests scripts

inventory:
	docker compose run --rm --no-deps runner inventory
