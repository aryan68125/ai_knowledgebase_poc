"""Integration tests for ingestion index to retrieval flow."""

from __future__ import annotations

from app.commands.index_chunks_command import IndexChunksCommand
from app.ingestion.indexing_pipeline import IngestionIndexingPipeline
from app.models.enums import ConnectorMode
from app.models.response_models import BaseResponse
from app.services.query_service import QueryService


def test_query_service_uses_ingested_chunks_after_pipeline_run() -> None:
    """After ingestion run, query service should retrieve source-backed indexed chunks."""

    index_command = IndexChunksCommand()
    index_command.clear_index()

    IngestionIndexingPipeline().run(mode=ConnectorMode.FULL)

    response: BaseResponse = QueryService().answer_user_query(
        query="runbook completeness and citation quality checks"
    )

    assert response.status == 200
    assert len(response.data["sources"]) > 0
    assert response.data["summary"] == "Answer generated from retrieved internal sources"
    assert any("Jira Knowledgebase Project" in source for source in response.data["sources"])
