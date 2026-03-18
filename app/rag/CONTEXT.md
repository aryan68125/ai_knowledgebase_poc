# RAG Folder Context

## Purpose
Own retrieval and context assembly behavior used before LLM generation.

## Responsibilities
- Implement retrieval pipeline components.
- Assemble context chunks for deterministic prompt input.
- Support citation-aware answer generation contracts.
- Keep business and execution decisions in backend code (not prompts).

## Boundaries
- Allowed imports: `app/core`, `app/models`.
- Prohibited: autonomous agent behavior or prompt-based business logic.

## File Context Registry
| File | Purpose | Depends On | Status |
| --- | --- | --- | --- |
| `CONTEXT.md` | Folder context and change tracking | `docs/AGENTS.md`, RAG docs | Active |
| `__init__.py` | RAG package marker | Python runtime | Active |
| `retriever.py` | Deterministic hybrid retrieval with in-memory corpus and ranking weights | `app/core/logger.py`, `app/models/query_models.py`, `app/models/enums.py` | Active |

## Auth Note
Authentication is intentionally deferred. Implement auth only after explicit user instruction in chat.

## Change Log
| Date | Change | Files | Notes |
| --- | --- | --- | --- |
| 2026-03-18 | Expanded structured logging coverage for retrieval paths | `retriever.py` | Added start/warning/success/error logs for deterministic hybrid retrieval execution |
| 2026-03-18 | Implemented hybrid retrieval ranking behavior | `retriever.py` | Added deterministic scoring (semantic, keyword, recency, trust) with top-k chunk selection |
| 2026-03-18 | Added initial RAG scaffold files | `__init__.py`, `retriever.py` | Introduced retrieval entry point returning typed retrieval results |
| 2026-03-18 | Initialized RAG folder context tracker | `CONTEXT.md` | Prepared retrieval-layer tracking |
