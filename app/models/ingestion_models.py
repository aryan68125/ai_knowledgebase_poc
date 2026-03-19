"""Typed models for ingestion, chunking, and indexing workflows."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConnectorMode, SourceType


class IngestionMetadata(BaseModel):
    """Metadata captured from source systems during ingestion."""

    model_config = ConfigDict(extra="forbid")

    source_type: SourceType
    document_id: str = Field(min_length=1)
    timestamp: datetime
    author: str = Field(min_length=1)
    project_key: str = Field(min_length=1)
    confidentiality: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    title: str = Field(min_length=1)


class IngestionDocument(BaseModel):
    """Normalized ingestion document payload."""

    model_config = ConfigDict(extra="forbid")

    metadata: IngestionMetadata
    text: str = Field(min_length=1)


class ConnectorFetchRequest(BaseModel):
    """Input contract for connector document retrieval."""

    model_config = ConfigDict(extra="forbid")

    mode: ConnectorMode


class ConnectorFetchResult(BaseModel):
    """Connector output payload with normalized documents."""

    model_config = ConfigDict(extra="forbid")

    documents: list[IngestionDocument]


class ChunkingRequest(BaseModel):
    """Input contract for chunk generation."""

    model_config = ConfigDict(extra="forbid")

    document: IngestionDocument
    chunk_size_tokens: int = Field(default=1000, ge=1, le=2000)
    chunk_overlap_tokens: int = Field(default=100, ge=0, le=500)


class IndexedChunk(BaseModel):
    """Chunk payload prepared for indexing."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_type: SourceType
    source_name: str = Field(min_length=1)
    project_key: str = Field(min_length=1)
    timestamp: datetime
    text: str = Field(min_length=1)
    token_count: int = Field(ge=1)


class ChunkingResult(BaseModel):
    """Output contract for chunking command."""

    model_config = ConfigDict(extra="forbid")

    chunks: list[IndexedChunk]


class IndexingRequest(BaseModel):
    """Input contract for index upsert command."""

    model_config = ConfigDict(extra="forbid")

    chunks: list[IndexedChunk]


class IndexingResult(BaseModel):
    """Output contract for index upsert command."""

    model_config = ConfigDict(extra="forbid")

    index_name: str
    indexed_count: int = Field(ge=0)
    total_index_size: int = Field(ge=0)
    last_indexed_at: datetime


class RunIngestionIndexingInput(BaseModel):
    """Input contract for ingestion indexing flow command."""

    model_config = ConfigDict(extra="forbid")

    documents: list[IngestionDocument]
    chunk_size_tokens: int = Field(default=1000, ge=1, le=2000)
    chunk_overlap_tokens: int = Field(default=100, ge=0, le=500)


class IngestionIndexingResult(BaseModel):
    """Result contract summarizing ingestion indexing run."""

    model_config = ConfigDict(extra="forbid")

    status: str
    documents_processed: int = Field(ge=0)
    chunks_created: int = Field(ge=0)
    chunks_indexed: int = Field(ge=0)
    index_name: str
