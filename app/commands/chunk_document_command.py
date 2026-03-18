"""Command to split ingestion documents into overlapping token chunks."""

from __future__ import annotations

from app.commands.base_command import BaseCommand
from app.core.logger import ATHENA_LOGGER
from app.models.ingestion_models import ChunkingRequest, ChunkingResult, IndexedChunk


class ChunkDocumentCommand(BaseCommand[ChunkingRequest, ChunkingResult]):
    """Generate deterministic overlapping chunks from a document."""

    def execute(self, input_model: ChunkingRequest) -> ChunkingResult:
        """Split a document into chunks using token-size and overlap settings."""

        try:
            ATHENA_LOGGER.info(
                module="app.commands.chunk_document_command",
                class_name="ChunkDocumentCommand",
                method="execute",
                message="Chunking command started",
                extra={
                    "document_id": input_model.document.metadata.document_id,
                    "chunk_size_tokens": input_model.chunk_size_tokens,
                    "chunk_overlap_tokens": input_model.chunk_overlap_tokens,
                },
            )

            stride = input_model.chunk_size_tokens - input_model.chunk_overlap_tokens
            if stride <= 0:
                raise ValueError("chunk_size_tokens must be greater than chunk_overlap_tokens")

            words = input_model.document.text.split()
            chunks: list[IndexedChunk] = []
            chunk_counter = 0

            for start in range(0, len(words), stride):
                chunk_words = words[start : start + input_model.chunk_size_tokens]
                if not chunk_words:
                    break

                chunk_counter += 1
                chunks.append(
                    IndexedChunk(
                        chunk_id=(
                            f"{input_model.document.metadata.document_id}-chunk-{chunk_counter}"
                        ),
                        document_id=input_model.document.metadata.document_id,
                        source_type=input_model.document.metadata.source_type,
                        source_name=input_model.document.metadata.source_name,
                        project_key=input_model.document.metadata.project_key,
                        timestamp=input_model.document.metadata.timestamp,
                        text=" ".join(chunk_words),
                        token_count=len(chunk_words),
                    )
                )

                if start + input_model.chunk_size_tokens >= len(words):
                    break

            ATHENA_LOGGER.info(
                module="app.commands.chunk_document_command",
                class_name="ChunkDocumentCommand",
                method="execute",
                message="Chunking command completed",
                extra={
                    "document_id": input_model.document.metadata.document_id,
                    "chunk_count": len(chunks),
                },
            )
            return ChunkingResult(chunks=chunks)
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.commands.chunk_document_command",
                class_name="ChunkDocumentCommand",
                method="execute",
                message="Chunking command failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[ChunkDocumentCommand.execute] {str(exc)}") from exc
