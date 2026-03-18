# Knowledgebase Project

Internal Knowledge Assistant backend scaffold built with FastAPI and a retrieval-first RAG pipeline.

## What This Project Does

This project is designed to answer internal knowledge questions using retrieved source context (Teams, SharePoint, Jira) and return source-backed responses.

Current implementation includes a working backend scaffold with:
- strict layered architecture (`api -> services -> commands -> rag -> ingestion -> models -> core`)
- typed Pydantic contracts
- standardized API response envelope
- deterministic retrieval behavior with hybrid ranking
- ingestion indexing pipeline (connector fetch -> chunking -> indexing)

Authentication is intentionally deferred and not implemented yet.

## How It Works

High-level flow:
1. API receives a user query.
2. Service orchestrates the retrieval-first pipeline.
3. RAG retriever runs deterministic hybrid ranking over an in-memory corpus.
4. Command builds a deterministic answer from retrieved context only.
5. API returns a standardized response model.

When no evidence is retrieved, the system returns:
- `"I don't know based on available information"`

For known project-domain queries (for example, onboarding runbooks), retrieval returns
citations from matched chunks.

## Project Structure

- `app/api/` FastAPI routes
- `app/services/` orchestration services (no business logic)
- `app/commands/` business logic via command classes
- `app/rag/` retrieval and context assembly components
- `app/ingestion/` connector and ingestion placeholders
- `app/ingestion/` connectors and indexing pipeline orchestration
- `app/logs/` runtime JSON log files
- `app/models/` shared Pydantic models and enums
- `app/core/` configuration and centralized logging
- `tests/` automated tests
- `docs/` architecture and planning docs

## Run This Project

From project root, run these commands:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip install uvicorn
```

If you prefer explicit install of env-loader dependency:

```bash
python -m pip install python-decouple
```

Start the API server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at:
- `http://127.0.0.1:8000`

## Logging

- Logs are written to `app/logs/app.log` by default.
- Logs are structured JSON lines.
- You can override log location with:
  - `LOG_DIR` (default: `app/logs`)
  - `LOG_FILE_NAME` (default: `app.log`)

## Environment Variables (`.env`)

This project loads configuration from a root `.env` file using `python-decouple`.

Current keys:
- `SERVICE_NAME`
- `API_PREFIX`
- `LOG_LEVEL`
- `LOG_DIR`
- `LOG_FILE_NAME`

## Ingestion Indexing Pipeline (Chunking + Index Command Flow)

The ingestion pipeline currently runs deterministic seed connector data and executes:
1. Connector fetch (Teams, SharePoint, Jira)
2. Chunk generation (`ChunkDocumentCommand`)
3. Index upsert (`IndexChunksCommand`)
4. Flow summary (`RunIngestionIndexingCommand`)

Run it manually:

```bash
python - <<'PY'
from app.ingestion.indexing_pipeline import IngestionIndexingPipeline
from app.models.enums import ConnectorMode

result = IngestionIndexingPipeline().run(mode=ConnectorMode.FULL)
print(result.model_dump())
PY
```

## Manual API Testing with Swagger (FastAPI)

1. Start the server with `uvicorn`.
2. Open Swagger UI: `http://127.0.0.1:8000/docs`
3. Expand `GET /api/v1/query`.
4. Click `Try it out`.
5. Enter a query value (example: `Where are runbooks stored?`).
6. Click `Execute`.
7. Inspect the response body, status code, and schema.

You can also use ReDoc at:
- `http://127.0.0.1:8000/redoc`

## Quick cURL Check

```bash
curl "http://127.0.0.1:8000/api/v1/query?query=Where%20are%20runbooks%20stored%3F"
```

## Run Tests

```bash
pytest -q
```

Expected at this stage:
- Tests pass for the initial query pipeline contract.
- Query endpoint returns standardized response format.
