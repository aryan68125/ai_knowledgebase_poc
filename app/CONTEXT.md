# App Root Context

## Purpose
Own package-level wiring and application entry point.

## Responsibilities
- Expose package root for imports.
- Build FastAPI app instance and mount API routers.
- Keep app bootstrap lightweight and deterministic.

## File Context Registry
| File | Purpose | Depends On | Status |
| --- | --- | --- | --- |
| `CONTEXT.md` | Root context and change tracking | `docs/AGENTS.md` | Active |
| `__init__.py` | App package marker | Python runtime | Active |
| `main.py` | FastAPI app factory, router mounting, and lifespan-based runtime lifecycle | `app/api/query_api.py`, `app/core/config.py`, `app/ingestion/automation.py` | Active |
| `logs/.gitkeep` | Keeps runtime log directory tracked in repository | Git | Active |
| `../.env` | Root environment variable file consumed by decouple config (including static-data ingestion and Hugging Face DeepSeek controls) | `app/core/config.py` | Active |
| `../.gitignore` | Root ignore policy for runtime/build artifacts (including local vector DB files) | Git | Active |

## Auth Note
Authentication is intentionally deferred. Implement auth only after explicit user instruction in chat.

## Change Log
| Date | Change | Files | Notes |
| --- | --- | --- | --- |
| 2026-03-18 | Added vector DB environment defaults and local artifact ignore rules | `../.env`, `../.gitignore` | Added `VECTOR_DB_*` settings and ignored `app/vector_db/` for local persistent index files |
| 2026-03-18 | Updated root environment defaults for static local data + Hugging Face LLM | `../.env` | Added `STATIC_*` and `HF_*` runtime keys while retaining legacy integration keys for future reactivation |
| 2026-03-18 | Extended root environment defaults for Teams Graph integration | `../.env` | Added Teams connector mode, credentials, and fetch tuning keys for mixed-mode ingestion |
| 2026-03-18 | Migrated app lifecycle hooks to FastAPI lifespan handlers | `main.py` | Replaced deprecated `on_event` usage with lifespan startup/shutdown runtime control |
| 2026-03-18 | Added app startup/shutdown lifecycle for auto-ingestion runtime | `main.py` | Wired auto-ingestion scheduler start/stop with config-based mode resolution |
| 2026-03-18 | Added repository tracking and environment files at root | `../.env`, `../.gitignore` | Added default env configuration and git hygiene for tracked development |
| 2026-03-18 | Added runtime log directory tracking | `logs/.gitkeep` | Established `app/logs` as the log output directory |
| 2026-03-18 | Added initial app root scaffold tracker | `CONTEXT.md`, `__init__.py`, `main.py` | Established package bootstrap and app factory wiring |
