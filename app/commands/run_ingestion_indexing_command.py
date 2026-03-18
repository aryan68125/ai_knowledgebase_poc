"""Command to orchestrate chunking and indexing for ingestion documents."""

from __future__ import annotations

from app.commands.base_command import BaseCommand
from app.commands.chunk_document_command import ChunkDocumentCommand
from app.commands.index_chunks_command import IndexChunksCommand
from app.core.logger import ATHENA_LOGGER
from app.models.ingestion_models import (
    ChunkingRequest,
    IndexedChunk,
    IngestionDocument,
    IngestionIndexingResult,
    IndexingRequest,
    RunIngestionIndexingInput,
)


class RunIngestionIndexingCommand(
    BaseCommand[RunIngestionIndexingInput, IngestionIndexingResult]
):
    """Execute end-to-end chunking and indexing over a document set."""

    def __init__(
        self,
        chunk_command: ChunkDocumentCommand | None = None,
        index_command: IndexChunksCommand | None = None,
    ) -> None:
        self._chunk_command = chunk_command or ChunkDocumentCommand()
        self._index_command = index_command or IndexChunksCommand()

    def execute(self, input_model: RunIngestionIndexingInput) -> IngestionIndexingResult:
        """Run chunk generation and index upsert flow for all input documents."""

        try:
            ATHENA_LOGGER.info(
                module="app.commands.run_ingestion_indexing_command",
                class_name="RunIngestionIndexingCommand",
                method="execute",
                message="Ingestion indexing flow started",
                extra={"documents_count": len(input_model.documents)},
            )

            all_chunks: list[IndexedChunk] = []
            for document in input_model.documents:
                chunking_result = self._chunk_command.execute(
                    input_model=document_to_chunk_request(
                        document=document,
                        chunk_size_tokens=input_model.chunk_size_tokens,
                        chunk_overlap_tokens=input_model.chunk_overlap_tokens,
                    )
                )
                all_chunks.extend(chunking_result.chunks)

            index_result = self._index_command.execute(IndexingRequest(chunks=all_chunks))

            summary = IngestionIndexingResult(
                status="completed",
                documents_processed=len(input_model.documents),
                chunks_created=len(all_chunks),
                chunks_indexed=index_result.indexed_count,
                index_name=index_result.index_name,
            )

            ATHENA_LOGGER.info(
                module="app.commands.run_ingestion_indexing_command",
                class_name="RunIngestionIndexingCommand",
                method="execute",
                message="Ingestion indexing flow completed",
                extra={
                    "documents_processed": summary.documents_processed,
                    "chunks_created": summary.chunks_created,
                    "chunks_indexed": summary.chunks_indexed,
                    "index_name": summary.index_name,
                },
            )
            return summary
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.commands.run_ingestion_indexing_command",
                class_name="RunIngestionIndexingCommand",
                method="execute",
                message="Ingestion indexing flow failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[RunIngestionIndexingCommand.execute] {str(exc)}") from exc


def document_to_chunk_request(
    document: IngestionDocument,
    chunk_size_tokens: int,
    chunk_overlap_tokens: int,
) -> ChunkingRequest:
    """Build chunking request model from ingestion document input."""

    ATHENA_LOGGER.debug(
        module="app.commands.run_ingestion_indexing_command",
        class_name="RunIngestionIndexingCommand",
        method="document_to_chunk_request",
        message="Building chunking request",
        extra={
            "document_id": document.metadata.document_id,
            "chunk_size_tokens": chunk_size_tokens,
            "chunk_overlap_tokens": chunk_overlap_tokens,
        },
    )
    return ChunkingRequest(
        document=document,
        chunk_size_tokens=chunk_size_tokens,
        chunk_overlap_tokens=chunk_overlap_tokens,
    )
