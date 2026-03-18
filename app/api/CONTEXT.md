# API Folder Context

## Purpose
Own the FastAPI layer for request handling, validation, and standardized responses.

## Responsibilities
- Define API routes and route-level dependencies.
- Validate request payloads with Pydantic models.
- Return standardized response models (`BaseResponse` pattern from `docs/AGENTS.md`).
- Delegate orchestration to services.

## Boundaries
- Allowed imports: `app/services`, `app/core` (central logger only).
- Prohibited: business logic in API handlers.

## File Context Registry
| File | Purpose | Depends On | Status |
| --- | --- | --- | --- |
| `CONTEXT.md` | Folder context and change tracking | `docs/AGENTS.md`, architecture docs | Active |
| `__init__.py` | API package marker | Python runtime | Active |
| `query_api.py` | Query endpoint definition, logging, and service delegation | `app/services/query_service.py`, `app/core/logger.py` | Active |

## Auth Note
Authentication is intentionally deferred. Implement auth only after explicit user instruction in chat.

## Change Log
| Date | Change | Files | Notes |
| --- | --- | --- | --- |
| 2026-03-18 | Added structured logging coverage to API endpoint | `query_api.py` | Added request start/success/failure logs for query endpoint execution |
| 2026-03-18 | Refined API endpoint contract handling | `query_api.py` | Added explicit return typing and defensive error wrapping |
| 2026-03-18 | Added initial API scaffold files | `__init__.py`, `query_api.py` | Created query route delegating to service orchestration |
| 2026-03-18 | Initialized API folder context tracker | `CONTEXT.md` | Bootstrapped tracking for upcoming API development |
