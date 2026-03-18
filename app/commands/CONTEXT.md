# Commands Folder Context

## Purpose
Own business logic through command classes following the command pattern.

## Responsibilities
- Implement command classes with explicit `execute` behavior.
- Enforce structured inputs and outputs via models.
- Contain business rules that services orchestrate.
- Raise explicit exceptions with class and method context.

## Boundaries
- Allowed imports: `app/models`, `app/core`.
- Prohibited: route concerns and API response formatting.

## File Context Registry
| File | Purpose | Depends On | Status |
| --- | --- | --- | --- |
| `CONTEXT.md` | Folder context and change tracking | `docs/AGENTS.md`, architecture docs | Active |
| `__init__.py` | Commands package marker | Python runtime | Active |
| `base_command.py` | Generic abstract command contract | `pydantic.BaseModel` | Active |
| `generate_answer_command.py` | Deterministic answer-construction command with structured logging | `app/models/query_models.py`, `app/models/response_models.py`, `app/core/logger.py` | Active |
| `chunk_document_command.py` | Token chunking command with overlap support | `app/models/ingestion_models.py`, `app/core/logger.py` | Active |
| `index_chunks_command.py` | Shared index-store upsert command with summary output | `app/models/ingestion_models.py`, `app/core/logger.py`, `app/core/index_store.py` | Active |
| `run_ingestion_indexing_command.py` | End-to-end command flow for chunking + indexing | `chunk_document_command.py`, `index_chunks_command.py`, `app/models/ingestion_models.py` | Active |

## Auth Note
Authentication is intentionally deferred. Implement auth only after explicit user instruction in chat.

## Change Log
| Date | Change | Files | Notes |
| --- | --- | --- | --- |
| 2026-03-18 | Wired indexing command to shared core index store | `index_chunks_command.py` | Replaced command-local storage with shared `app/core/index_store.py` integration |
| 2026-03-18 | Added structured logging coverage to answer-generation command | `generate_answer_command.py` | Added start/success/warning/failure logs for response construction paths |
| 2026-03-18 | Added ingestion indexing command flow | `chunk_document_command.py`, `index_chunks_command.py`, `run_ingestion_indexing_command.py` | Implemented chunk creation, index upsert, and orchestration command with structured logging |
| 2026-03-18 | Added initial command scaffold files | `__init__.py`, `base_command.py`, `generate_answer_command.py` | Established command pattern and first answer-generation command |
| 2026-03-18 | Initialized commands folder context tracker | `CONTEXT.md` | Prepared business-logic tracking |
