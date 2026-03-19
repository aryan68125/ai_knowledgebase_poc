"""Command to upsert chunks into configured vector-store provider."""

from __future__ import annotations

from datetime import datetime, timezone

from app.commands.base_command import BaseCommand
from app.core.index_store import INDEX_STORE
from app.core.logger import ATHENA_LOGGER
from app.core.text_embedder import TEXT_EMBEDDER
from app.core.vector_store import VECTOR_STORE
from app.models.ingestion_models import IndexingRequest, IndexingResult


class IndexChunksCommand(BaseCommand[IndexingRequest, IndexingResult]):
    """Upsert chunk vectors and metadata into configured vector store."""

    def execute(self, input_model: IndexingRequest) -> IndexingResult:
        """Index chunks and return indexing summary."""

        try:
            ATHENA_LOGGER.info(
                module="app.commands.index_chunks_command",
                class_name="IndexChunksCommand",
                method="execute",
                message="Indexing command started",
                extra={"incoming_chunks": len(input_model.chunks)},
            )

            records = [chunk.model_dump(mode="json") for chunk in input_model.chunks]
            # Use embed_many() when available (HuggingFaceEmbedder) to batch all
            # chunks into a small number of API calls instead of N individual ones.
            texts = [chunk.text for chunk in input_model.chunks]
            if hasattr(TEXT_EMBEDDER, "embed_many"):
                vectors = TEXT_EMBEDDER.embed_many(texts)
            else:
                vectors = [TEXT_EMBEDDER.embed(t) for t in texts]
            total_index_size = VECTOR_STORE.upsert_many(records=records, vectors=vectors)
            INDEX_STORE.upsert_many(records=records)

            result = IndexingResult(
                index_name=VECTOR_STORE.index_name,
                indexed_count=len(input_model.chunks),
                total_index_size=total_index_size,
                last_indexed_at=datetime.now(timezone.utc),
            )

            ATHENA_LOGGER.info(
                module="app.commands.index_chunks_command",
                class_name="IndexChunksCommand",
                method="execute",
                message="Indexing command completed",
                extra={
                    "indexed_count": result.indexed_count,
                    "total_index_size": result.total_index_size,
                    "index_name": result.index_name,
                },
            )
            return result
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.commands.index_chunks_command",
                class_name="IndexChunksCommand",
                method="execute",
                message="Indexing command failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[IndexChunksCommand.execute] {str(exc)}") from exc

    @classmethod
    def clear_index(cls) -> None:
        """Reset configured vector store for tests and deterministic runs."""

        VECTOR_STORE.clear()
        INDEX_STORE.clear()
        ATHENA_LOGGER.info(
            module="app.commands.index_chunks_command",
            class_name="IndexChunksCommand",
            method="clear_index",
            message="Vector store and lexical index store cleared through command API",
        )
