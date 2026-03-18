# Core Folder Context

## Purpose
Own foundational infrastructure shared across layers (config, logging, low-level utilities).

## Responsibilities
- Centralize configuration in `app/core/config.py`.
- Centralize structured logging in `app/core/logger.py`.
- Host reusable low-level utilities and cross-cutting concerns.
- Enforce no upward imports into higher-level layers.

## Boundaries
- Core is dependency-bottom: no upward imports.
- Must not contain feature-specific business rules.

## File Context Registry
| File | Purpose | Depends On | Status |
| --- | --- | --- | --- |
| `CONTEXT.md` | Folder context and change tracking | `docs/AGENTS.md`, operations docs | Active |
| `__init__.py` | Core package marker | Python runtime | Active |
| `config.py` | Centralized runtime settings loading (including `.env`, logging, and auto-ingestion scheduler settings) | `os`, `pathlib`, Pydantic, `python-decouple` | Active |
| `logger.py` | Centralized structured ATHENA-style logger (stream + file output) | `logging`, `json`, `pathlib`, `app/core/config.py` | Active |
| `index_store.py` | Shared in-memory index store for ingestion and retrieval | `typing`, `app/core/logger.py` | Active |

## Auth Note
Authentication is intentionally deferred. Implement auth only after explicit user instruction in chat.

## Change Log
| Date | Change | Files | Notes |
| --- | --- | --- | --- |
| 2026-03-18 | Added shared index store for ingestion-to-retrieval flow | `index_store.py` | Introduced shared in-memory indexed record store used by indexing commands and retriever |
| 2026-03-18 | Added auto-ingestion scheduler configuration keys | `config.py` | Added `AUTO_INGESTION_ENABLED`, `AUTO_INGESTION_INTERVAL_SECONDS`, and `AUTO_INGESTION_MODE` settings |
| 2026-03-18 | Added `.env`-based configuration loading | `config.py` | Integrated `python-decouple` with search-path aware settings loader |
| 2026-03-18 | Enabled file-based logging in `app/logs` | `config.py`, `logger.py` | Added `LOG_DIR` and `LOG_FILE_NAME` settings and configured `FileHandler` output |
| 2026-03-18 | Added initial core scaffold files | `__init__.py`, `config.py`, `logger.py` | Implemented centralized configuration and structured logging primitives |
| 2026-03-18 | Initialized core folder context tracker | `CONTEXT.md` | Prepared shared-infrastructure tracking |
