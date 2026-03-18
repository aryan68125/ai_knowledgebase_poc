# Models Folder Context

## Purpose
Own shared typed contracts for API, services, commands, and RAG layers.

## Responsibilities
- Define Pydantic request and response models.
- Define command input and output schemas.
- Define centralized enums in `app/models/enums.py`.
- Enforce strict model configuration (`extra = "forbid"` where required).

## Boundaries
- Shared dependency layer for typed interfaces.
- Prohibited: embedding orchestration or business logic.

## File Context Registry
| File | Purpose | Depends On | Status |
| --- | --- | --- | --- |
| `CONTEXT.md` | Folder context and change tracking | `docs/AGENTS.md`, architecture docs | Active |
| `__init__.py` | Models package marker | Python runtime | Active |
| `enums.py` | Centralized enums (`SourceType`, `ConnectorMode`) | Python `enum` | Active |
| `query_models.py` | Retrieval request/result and chunk models | `app/models/enums.py`, Pydantic | Active |
| `response_models.py` | Standardized `BaseResponse` and typed query answer model | Pydantic | Active |
| `ingestion_models.py` | Ingestion, chunking, and indexing flow contracts | `app/models/enums.py`, Pydantic, `datetime` | Active |

## Auth Note
Authentication is intentionally deferred. Implement auth only after explicit user instruction in chat.

## Change Log
| Date | Change | Files | Notes |
| --- | --- | --- | --- |
| 2026-03-18 | Added ingestion workflow models | `ingestion_models.py` | Added normalized connector document, chunking, indexing, and pipeline summary contracts |
| 2026-03-18 | Added initial models scaffold files | `__init__.py`, `enums.py`, `query_models.py`, `response_models.py` | Added strict typed contracts for retrieval and response layers |
| 2026-03-18 | Initialized models folder context tracker | `CONTEXT.md` | Prepared typed-contract tracking |
