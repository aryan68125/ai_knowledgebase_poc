"""Tests for local Qdrant vector-store implementation."""

from __future__ import annotations

from app.core.text_embedder import HashTokenEmbedder
from app.core.vector_store import QdrantLocalVectorStore


def test_qdrant_local_store_upsert_and_query(tmp_path) -> None:
    """Qdrant local store should persist vectors and return relevant matches."""

    embedder = HashTokenEmbedder(dimension=64)
    store = QdrantLocalVectorStore(
        collection_name="kb_test_collection",
        path=str(tmp_path / "qdrant"),
        vector_size=64,
    )
    store.clear()

    records = [
        {
            "chunk_id": "chunk-1",
            "source_type": "sharepoint",
            "source_name": "Local Documents / proposal.docx",
            "text": "The proposal describes microservices migration and cost optimization.",
        },
        {
            "chunk_id": "chunk-2",
            "source_type": "teams",
            "source_name": "Local Chat Data / team_chat_1.json",
            "text": "The team discussed runbook completeness and citation quality checks.",
        },
    ]
    vectors = [embedder.embed(record["text"]) for record in records]

    total_size = store.upsert_many(records=records, vectors=vectors)
    assert total_size == 2

    query_vector = embedder.embed("runbook citation quality checks")
    matches = store.query(vector=query_vector, top_k=2)

    assert len(matches) > 0
    assert any("Local Chat Data" in match.get("source_name", "") for match in matches)


def test_qdrant_local_store_clear_resets_collection(tmp_path) -> None:
    """Qdrant local store clear should remove all points from collection."""

    embedder = HashTokenEmbedder(dimension=32)
    store = QdrantLocalVectorStore(
        collection_name="kb_test_collection_clear",
        path=str(tmp_path / "qdrant"),
        vector_size=32,
    )
    store.clear()
    store.upsert_many(
        records=[
            {
                "chunk_id": "chunk-clear-1",
                "source_type": "teams",
                "source_name": "Local Chat Data / team_chat_2.json",
                "text": "Temporary test payload",
            }
        ],
        vectors=[embedder.embed("Temporary test payload")],
    )
    assert store.size() == 1

    store.clear()

    assert store.size() == 0
