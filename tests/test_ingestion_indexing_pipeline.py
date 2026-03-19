"""Tests for ingestion chunking and indexing command flow."""

from __future__ import annotations

from datetime import datetime, timezone

from app.commands.chunk_document_command import ChunkDocumentCommand
from app.commands.index_chunks_command import IndexChunksCommand
from app.ingestion.indexing_pipeline import IngestionIndexingPipeline
from app.models.enums import ConnectorMode, SourceType
from app.models.ingestion_models import (
    ChunkingRequest,
    IndexedChunk,
    IndexingRequest,
    IngestionDocument,
    IngestionMetadata,
)


def _build_document(text: str, document_id: str = "doc-1") -> IngestionDocument:
    return IngestionDocument(
        metadata=IngestionMetadata(
            source_type=SourceType.SHAREPOINT,
            document_id=document_id,
            timestamp=datetime.now(timezone.utc),
            author="platform-team",
            project_key="KB",
            confidentiality="internal",
            source_name="SharePoint Engineering Runbooks",
            title="Onboarding Runbooks",
        ),
        text=text,
    )


def test_chunk_document_command_single_para_under_limit() -> None:
    """A document with one paragraph under the max should produce exactly one chunk."""

    command = ChunkDocumentCommand()
    document = _build_document("word1 word2 word3 word4 word5")

    result = command.execute(
        ChunkingRequest(document=document, chunk_size_tokens=10, chunk_overlap_tokens=2)
    )

    assert len(result.chunks) == 1
    assert result.chunks[0].text == "word1 word2 word3 word4 word5"
    assert result.chunks[0].chunk_id == "doc-1-chunk-1"


def test_chunk_document_command_aggregates_small_paragraphs() -> None:
    """Document with two small paragraphs under the limit should produce one aggregated chunk."""

    command = ChunkDocumentCommand()
    paragraph_a = "sentence one. sentence two."
    paragraph_b = "sentence three. sentence four."
    document = _build_document(f"{paragraph_a}\n\n{paragraph_b}")

    result = command.execute(
        ChunkingRequest(document=document, chunk_size_tokens=100, chunk_overlap_tokens=0)
    )

    assert len(result.chunks) == 1
    assert result.chunks[0].text == f"{paragraph_a} {paragraph_b}"


def test_chunk_document_command_overlap_respects_token_limit() -> None:
    """Overlap words from chunk N should appear in chunk N+1, without exceeding chunk limit."""

    command = ChunkDocumentCommand()
    # 6 words total
    text = "alpha beta gamma delta epsilon zeta"
    document = _build_document(text)

    # Max 4 words per chunk, 2 words overlap
    result = command.execute(
        ChunkingRequest(document=document, chunk_size_tokens=4, chunk_overlap_tokens=2)
    )

    # Chunks should be exactly max 4 words:
    # 1: alpha beta gamma delta (4 words)
    # 2: gamma delta epsilon zeta (4 words)
    
    assert len(result.chunks) == 2
    assert result.chunks[0].text == "alpha beta gamma delta"
    assert result.chunks[1].text == "gamma delta epsilon zeta"
    assert result.chunks[0].token_count == 4
    assert result.chunks[1].token_count == 4


def test_index_chunks_command_upserts_and_tracks_total_index_size() -> None:
    """Index command should upsert chunks and keep unique chunk ids."""

    command = IndexChunksCommand()
    command.clear_index()

    chunks = [
        IndexedChunk(
            chunk_id="doc-1-chunk-1",
            document_id="doc-1",
            source_type=SourceType.SHAREPOINT,
            source_name="SharePoint Engineering Runbooks",
            project_key="KB",
            timestamp=datetime.now(timezone.utc),
            text="onboarding runbook details",
            token_count=3,
        ),
        IndexedChunk(
            chunk_id="doc-1-chunk-2",
            document_id="doc-1",
            source_type=SourceType.SHAREPOINT,
            source_name="SharePoint Engineering Runbooks",
            project_key="KB",
            timestamp=datetime.now(timezone.utc),
            text="environment setup steps",
            token_count=3,
        ),
    ]

    first_result = command.execute(IndexingRequest(chunks=chunks))
    second_result = command.execute(IndexingRequest(chunks=chunks))

    assert first_result.indexed_count == 2
    assert first_result.total_index_size == 2
    assert second_result.indexed_count == 2
    assert second_result.total_index_size == 2


def test_ingestion_indexing_pipeline_processes_documents_and_indexes_chunks() -> None:
    """Ingestion pipeline should fetch docs, chunk them, and index created chunks."""

    pipeline = IngestionIndexingPipeline()
    result = pipeline.run(mode=ConnectorMode.FULL)

    assert result.status == "completed"
    assert result.documents_processed > 0
    assert result.chunks_created > 0
    assert result.chunks_indexed > 0
