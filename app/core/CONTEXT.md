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
| `config.py` | Centralized runtime settings loading (including static data directories, Hugging Face LLM config, vector DB provider controls, `.env`, logging, scheduler controls, and legacy integration keys) | `os`, `pathlib`, Pydantic, `python-decouple` | Active |
| `logger.py` | Centralized structured ATHENA-style logger (stream + file output) | `logging`, `json`, `pathlib`, `app/core/config.py` | Active |
| `index_store.py` | In-memory lexical mirror index supporting retrieval fallback/enrichment paths | `typing`, `app/core/logger.py` | Active |
| `text_embedder.py` | Deterministic token-hash embedder used by indexing and retrieval query vectorization | `hashlib`, `math`, `re`, `app/core/config.py`, `app/core/logger.py` | Active |
| `vector_store.py` | Vector store abstraction with `qdrant_local` provider and in-memory fallback provider | `pathlib`, `uuid`, `qdrant-client`, `app/core/config.py`, `app/core/logger.py` | Active |
| `huggingface_client.py` | Low-level Hugging Face chat completion client used by answer command | `urllib`, `json`, `app/core/config.py`, `app/core/logger.py` | Active |

## Auth Note
Authentication is intentionally deferred. Implement auth only after explicit user instruction in chat.

## Change Log
| Date | Change | Files | Notes |
| --- | --- | --- | --- |
| 2026-03-19 | Reactivated in-memory index store as lexical retrieval companion | `index_store.py` | Used as a supplemental lexical evidence source alongside vector retrieval to improve precision for direct fact queries |
| 2026-03-19 | Strengthened HF prompt contract to request raw JSON-only output | `huggingface_client.py` | Added explicit instruction to avoid `<think>` tags, markdown fences, and extra commentary so downstream answer parsing stays clean |
| 2026-03-18 | Added local vector DB core layer with deterministic embeddings | `vector_store.py`, `text_embedder.py`, `config.py` | Introduced provider-driven vector store (`qdrant_local` default), deterministic hash-token embedding, and vector DB env configuration |
| 2026-03-18 | Added Hugging Face DeepSeek-R1 client and config controls | `huggingface_client.py`, `config.py` | Added chat completion client, HF token/model/runtime knobs, and structured logging across LLM calls |
| 2026-03-18 | Added Teams connector mixed-mode configuration keys | `config.py` | Added env-driven controls for Teams Graph auth, mode switching, pagination, and metadata defaults |
| 2026-03-18 | Added shared index store for ingestion-to-retrieval flow | `index_store.py` | Introduced shared in-memory indexed record store used by indexing commands and retriever |
| 2026-03-18 | Added auto-ingestion scheduler configuration keys | `config.py` | Added `AUTO_INGESTION_ENABLED`, `AUTO_INGESTION_INTERVAL_SECONDS`, and `AUTO_INGESTION_MODE` settings |
| 2026-03-18 | Added `.env`-based configuration loading | `config.py` | Integrated `python-decouple` with search-path aware settings loader |
| 2026-03-18 | Enabled file-based logging in `app/logs` | `config.py`, `logger.py` | Added `LOG_DIR` and `LOG_FILE_NAME` settings and configured `FileHandler` output |
| 2026-03-18 | Added initial core scaffold files | `__init__.py`, `config.py`, `logger.py` | Implemented centralized configuration and structured logging primitives |
| 2026-03-18 | Initialized core folder context tracker | `CONTEXT.md` | Prepared shared-infrastructure tracking |
