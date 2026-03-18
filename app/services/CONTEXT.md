# Services Folder Context

## Purpose
Own application orchestration services that coordinate commands, RAG, and model flows.

## Responsibilities
- Orchestrate command execution and RAG interactions.
- Keep services thin; no business logic in service classes.
- Provide typed service interfaces for API layer usage.

## Boundaries
- Allowed imports: `app/commands`, `app/rag`, `app/models`, `app/core` (central logger only).
- Prohibited: embedding business rules directly in services.

## File Context Registry
| File | Purpose | Depends On | Status |
| --- | --- | --- | --- |
| `CONTEXT.md` | Folder context and change tracking | `docs/AGENTS.md`, architecture docs | Active |
| `__init__.py` | Services package marker | Python runtime | Active |
| `query_service.py` | Retrieval-first query orchestration service with structured logging | `app/commands/generate_answer_command.py`, `app/rag/retriever.py`, `app/models/response_models.py`, `app/core/logger.py` | Active |

## Auth Note
Authentication is intentionally deferred. Implement auth only after explicit user instruction in chat.

## Change Log
| Date | Change | Files | Notes |
| --- | --- | --- | --- |
| 2026-03-18 | Added structured logging coverage to query service flow | `query_service.py` | Added logs for start, retrieval step, success, and failure paths |
| 2026-03-18 | Aligned service imports to architecture boundaries | `query_service.py` | Removed direct core dependency to keep service imports within allowed layers |
| 2026-03-18 | Added initial service scaffold files | `__init__.py`, `query_service.py` | Implemented thin service orchestration with standardized response envelope |
| 2026-03-18 | Initialized services folder context tracker | `CONTEXT.md` | Prepared orchestration-layer tracking |
