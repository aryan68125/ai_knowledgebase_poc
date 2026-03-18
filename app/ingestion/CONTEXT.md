# Ingestion Folder Context

## Purpose
Own data connector, preprocessing, chunking, and indexing workflows for knowledge ingestion.

## Responsibilities
- Integrate source connectors (Teams, SharePoint, Jira).
- Handle full backfill and incremental updates.
- Normalize content and preserve meaningful structure.
- Produce chunked, metadata-rich artifacts for embedding/indexing.

## Boundaries
- Primary references: `docs/02-ingestion/connectors_and_indexing.md`.
- Keep ingestion deterministic and auditable.
- Avoid introducing auth implementation here until explicitly requested.

## File Context Registry
| File | Purpose | Depends On | Status |
| --- | --- | --- | --- |
| `CONTEXT.md` | Folder context and change tracking | `docs/AGENTS.md`, ingestion docs | Active |
| `__init__.py` | Ingestion package marker | Python runtime | Active |
| `connectors.py` | Connector base class and deterministic source document fetchers | `app/models/enums.py`, `app/models/ingestion_models.py`, `app/core/logger.py` | Active |
| `indexing_pipeline.py` | Pipeline orchestration for connector fetch + chunk/index command flow | `app/ingestion/connectors.py`, `app/commands/run_ingestion_indexing_command.py` | Active |
| `automation.py` | Background scheduler and lifecycle runtime for auto-ingestion | `app/ingestion/indexing_pipeline.py`, `app/models/enums.py`, `app/core/logger.py`, `threading` | Active |

## Auth Note
Authentication is intentionally deferred. Implement auth only after explicit user instruction in chat.

## Change Log
| Date | Change | Files | Notes |
| --- | --- | --- | --- |
| 2026-03-18 | Added ingestion-to-retrieval shared index integration | `indexing_pipeline.py` | Pipeline-indexed chunks are now consumed by retriever via shared core index store |
| 2026-03-18 | Added automatic ingestion scheduler runtime | `automation.py` | Added periodic ingestion scheduler and enable/disable runtime wrapper with structured logging |
| 2026-03-18 | Implemented ingestion indexing pipeline orchestration | `indexing_pipeline.py`, `connectors.py` | Added connector fetch normalization and end-to-end pipeline execution with structured logs |
| 2026-03-18 | Added explicit integration exception wrapping | `connectors.py` | Applied required exception format for connector integration boundaries |
| 2026-03-18 | Added initial ingestion scaffold files | `__init__.py`, `connectors.py` | Added connector interfaces/placeholders for Teams, SharePoint, and Jira |
| 2026-03-18 | Initialized ingestion folder context tracker | `CONTEXT.md` | Prepared connector/indexing tracking |
