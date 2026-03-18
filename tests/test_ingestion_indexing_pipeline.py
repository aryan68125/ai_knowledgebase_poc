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


def test_chunk_document_command_splits_text_with_overlap() -> None:
    """Chunk command should split text by token size and preserve overlap."""

    command = ChunkDocumentCommand()
    document = _build_document("word1 word2 word3 word4 word5 word6 word7 word8 word9 word10")

    result = command.execute(
        ChunkingRequest(document=document, chunk_size_tokens=5, chunk_overlap_tokens=2)
    )

    assert len(result.chunks) == 3
    assert result.chunks[0].token_count == 5
    assert result.chunks[1].text.startswith("word4 word5")
    assert result.chunks[2].chunk_id == "doc-1-chunk-3"


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
