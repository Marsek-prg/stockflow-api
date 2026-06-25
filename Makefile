.PHONY: install test lint format-check format check coverage docker-build

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

format-check:
	black --check .

format:
	black .

check:
	ruff check . && black --check . && pytest

coverage:
	pytest --cov=app --cov-report=term-missing

docker-build:
	docker build -t stockflow-api .
