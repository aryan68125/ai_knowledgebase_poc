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
    assert isinstance(response.data["summary"], str) and len(response.data["summary"]) > 0
    assert any(
        ("Local Chat Data /" in source) or ("Local Documents /" in source)
        for source in response.data["sources"]
    )


def test_query_service_returns_cloud_cost_signal_for_cost_query() -> None:
    """Cost query should retrieve evidence containing the current cloud-cost numbers."""

    index_command = IndexChunksCommand()
    index_command.clear_index()
    IngestionIndexingPipeline().run(mode=ConnectorMode.FULL)

    response: BaseResponse = QueryService().answer_user_query(
        query="What is the current cloud cost?"
    )

    detailed_explanation = str(response.data["detailed_explanation"])
    sources = response.data["sources"]

    assert response.status == 200
    assert "18,200" in detailed_explanation
    assert any("team_chat_1.json" in source for source in sources)
