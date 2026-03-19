# Local Qdrant Vector DB Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local, persistent vector database (Qdrant local mode) so ingestion writes chunk embeddings to vector storage and retrieval queries vectors instead of relying only on in-memory records.

**Architecture:** Introduce a vector-store abstraction in `app/core/` with a Qdrant-backed implementation and deterministic embedding generator. Update indexing command to upsert chunk vectors and retriever to query vector store first, with seed-corpus fallback if vector store is empty. Keep logging and exception conventions intact.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, `qdrant-client` (local mode), existing command/retriever layers.

---

### Task 1: Add failing tests for vector store behavior

**Files:**
- Create: `tests/test_vector_store_qdrant.py`
- Modify: `tests/test_ingestion_to_retrieval_integration.py`

**Step 1: Write failing tests**

Add tests that validate:
- Qdrant local store upserts records and returns non-empty query matches.
- Clearing index removes stored vectors.
- Ingestion -> retrieval integration still returns source-backed answers with vector-backed retrieval.

**Step 2: Run tests to verify fail**

Run:
- `.venv/bin/python -m pytest tests/test_vector_store_qdrant.py tests/test_ingestion_to_retrieval_integration.py -q`

Expected: FAIL before implementation.

### Task 2: Implement vector store abstraction + Qdrant local provider

**Files:**
- Create: `app/core/text_embedder.py`
- Create: `app/core/vector_store.py`
- Modify: `app/core/config.py`
- Modify: `.env`
- Modify: `pyproject.toml`

**Step 1: Minimal implementation**

Add:
- deterministic embedding function (hash-token vector)
- vector-store protocol and two providers:
  - in-memory provider
  - local-qdrant provider (persistent path)
- config keys to control provider/path/collection/top-k/dimension.

**Step 2: Verify with tests**

Run:
- `.venv/bin/python -m pytest tests/test_vector_store_qdrant.py tests/test_config.py -q`

Expected: PASS.

### Task 3: Wire indexing + retrieval to vector store

**Files:**
- Modify: `app/commands/index_chunks_command.py`
- Modify: `app/rag/retriever.py`

**Step 1: Write/adjust failing behavior tests**

Ensure integration test validates vector-backed retrieval path still returns sources.

**Step 2: Implement**

- Indexing command: embed and upsert chunk vectors + metadata.
- Retriever: query vector store for top-k chunk payloads and convert to `RetrievalChunk`.
- Keep fallback to seed corpus when vector store empty.

**Step 3: Verify**

Run:
- `.venv/bin/python -m pytest tests/test_ingestion_indexing_pipeline.py tests/test_ingestion_to_retrieval_integration.py tests/test_query_pipeline.py -q`

Expected: PASS.

### Task 4: Documentation + context tracking updates

**Files:**
- Modify: `README.md`
- Modify: `app/core/CONTEXT.md`
- Modify: `app/commands/CONTEXT.md`
- Modify: `app/rag/CONTEXT.md`
- Modify: `app/CONTEXT.md`

**Step 1: Update docs**

Document:
- Qdrant local mode location/path
- env keys
- manual test steps
- how to clear/rebuild index

**Step 2: Verify docs references**

Run:
- `rg -n "Qdrant|VECTOR_DB|vector" README.md app/*/CONTEXT.md app/CONTEXT.md`

Expected: coherent references.

### Task 5: Full verification

**Step 1: Run full tests**

Run:
- `.venv/bin/python -m pytest -q`

Expected: all tests pass.
