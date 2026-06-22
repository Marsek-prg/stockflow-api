# StockFlow API

StockFlow API is a REST API foundation for inventory, warehouse stock, and order
management. It provides a versioned FastAPI application, PostgreSQL persistence
configuration, database migration tooling, automated tests, and containerized
local infrastructure.

## Tech Stack

- Python 3.12
- FastAPI and Uvicorn
- PostgreSQL 16
- SQLAlchemy 2.0 and Alembic
- Pydantic v2 and pydantic-settings
- pytest and HTTPX
- Ruff and Black
- Docker and Docker Compose

## Project Structure

```text
app/
├── api/v1/          # Versioned API routes
├── core/            # Application configuration
├── db/              # SQLAlchemy base and session factory
├── models/          # Database models
├── schemas/         # Request and response schemas
├── services/        # Application services
└── main.py           # FastAPI application entry point
alembic/              # Database migration environment
tests/                # Automated tests
```

## Local Development

Python 3.12 and a running PostgreSQL instance are required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

On Windows PowerShell, activate the environment with
`.venv\\Scripts\\Activate.ps1` and copy the environment file with
`Copy-Item .env.example .env`.

## Docker Setup

Start the API and PostgreSQL services:

```bash
docker compose up --build
```

The API is exposed on port `8000`, and PostgreSQL is exposed on port `5432`.

## API Docs

- Swagger UI: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/v1/health

## Tests

Run the test suite:

```bash
pytest
```

Run code-quality checks:

```bash
ruff check .
black --check .
```

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `PROJECT_NAME` | `StockFlow API` | Application name shown in OpenAPI documentation. |
| `API_V1_PREFIX` | `/api/v1` | URL prefix for version 1 endpoints. |
| `DATABASE_URL` | `postgresql+psycopg://stockflow:stockflow@localhost:5432/stockflow` | SQLAlchemy PostgreSQL connection URL. |

Copy `.env.example` to `.env` to override local settings. Docker Compose supplies
the service-network database URL automatically.
