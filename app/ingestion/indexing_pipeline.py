"""Ingestion indexing pipeline orchestration."""

from __future__ import annotations

from app.commands.run_ingestion_indexing_command import RunIngestionIndexingCommand
from app.core.logger import ATHENA_LOGGER
from app.ingestion.connectors import BaseConnector, JiraConnector, SharePointConnector, TeamsConnector
from app.models.enums import ConnectorMode
from app.models.ingestion_models import IngestionIndexingResult, RunIngestionIndexingInput


class IngestionIndexingPipeline:
    """Fetch documents from connectors and execute chunking + indexing command flow."""

    def __init__(
        self,
        connectors: list[BaseConnector] | None = None,
        run_command: RunIngestionIndexingCommand | None = None,
    ) -> None:
        self._connectors = connectors or [TeamsConnector(), SharePointConnector(), JiraConnector()]
        self._run_command = run_command or RunIngestionIndexingCommand()

    def run(
        self,
        mode: ConnectorMode,
        chunk_size_tokens: int = 600,
        chunk_overlap_tokens: int = 80,
    ) -> IngestionIndexingResult:
        """Execute ingestion fetch + chunking + indexing flow."""

        try:
            ATHENA_LOGGER.info(
                module="app.ingestion.indexing_pipeline",
                class_name="IngestionIndexingPipeline",
                method="run",
                message="Ingestion indexing pipeline started",
                extra={
                    "mode": mode.value,
                    "connectors_count": len(self._connectors),
                    "chunk_size_tokens": chunk_size_tokens,
                    "chunk_overlap_tokens": chunk_overlap_tokens,
                },
            )

            documents = []
            for connector in self._connectors:
                connector_result = connector.fetch_documents(mode=mode)
                documents.extend(connector_result.documents)

            result = self._run_command.execute(
                RunIngestionIndexingInput(
                    documents=documents,
                    chunk_size_tokens=chunk_size_tokens,
                    chunk_overlap_tokens=chunk_overlap_tokens,
                )
            )

            ATHENA_LOGGER.info(
                module="app.ingestion.indexing_pipeline",
                class_name="IngestionIndexingPipeline",
                method="run",
                message="Ingestion indexing pipeline completed",
                extra={
                    "mode": mode.value,
                    "documents_processed": result.documents_processed,
                    "chunks_indexed": result.chunks_indexed,
                },
            )
            return result
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.indexing_pipeline",
                class_name="IngestionIndexingPipeline",
                method="run",
                message="Ingestion indexing pipeline failed",
                extra={"error": str(exc), "mode": mode.value},
            )
            raise Exception(f"[IngestionIndexingPipeline.run] {str(exc)}") from exc
