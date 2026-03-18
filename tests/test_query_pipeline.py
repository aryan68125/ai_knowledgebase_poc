"""Contract tests for the initial query pipeline scaffold."""

from __future__ import annotations

from fastapi import status
from pydantic import ValidationError

from app.api.query_api import query_endpoint
from app.commands.generate_answer_command import GenerateAnswerCommand, GenerateAnswerInput
from app.models.query_models import RetrievalRequest
from app.models.response_models import BaseResponse
from app.rag.retriever import Retriever
from app.services.query_service import QueryService


def test_base_response_forbids_extra_fields() -> None:
    """BaseResponse must reject undeclared fields to keep contracts strict."""

    try:
        BaseResponse(status=status.HTTP_200_OK, message="ok", data={}, extra_field="nope")
    except ValidationError:
        pass
    else:
        raise AssertionError("Expected BaseResponse to reject extra fields")


def test_generate_answer_command_returns_uncertainty_without_context() -> None:
    """Command returns deterministic uncertainty when retrieval has no evidence."""

    command: GenerateAnswerCommand = GenerateAnswerCommand()
    output = command.execute(
        GenerateAnswerInput(query="How do we deploy this service?", retrieved_chunks=[])
    )

    assert output.summary == "I don't know based on available information"
    assert output.sources == []


def test_query_service_returns_standard_base_response_shape() -> None:
    """Service must return standardized BaseResponse model."""

    service: QueryService = QueryService()
    response: BaseResponse = service.answer_user_query(query="What is the onboarding flow?")

    assert response.status == status.HTTP_200_OK
    assert isinstance(response.message, str)
    assert set(response.data.keys()) == {"summary", "detailed_explanation", "sources"}


def test_retriever_returns_results_for_known_domain_query() -> None:
    """Retriever should return at least one chunk for known project-domain topics."""

    retriever: Retriever = Retriever()
    retrieval_result = retriever.retrieve(request=RetrievalRequest(query="onboarding runbooks"))

    assert len(retrieval_result.chunks) > 0


def test_query_service_returns_citations_for_known_domain_query() -> None:
    """Service response should include citations when retrieval finds evidence."""

    service: QueryService = QueryService()
    response: BaseResponse = service.answer_user_query(query="Where are onboarding runbooks stored?")

    assert response.status == status.HTTP_200_OK
    assert len(response.data["sources"]) > 0
    assert response.data["summary"] != "I don't know based on available information"


def test_query_api_endpoint_returns_base_response_payload() -> None:
    """API endpoint function should expose the standardized response contract."""

    payload: BaseResponse = query_endpoint(query="Where are runbooks stored?")

    assert payload.status == status.HTTP_200_OK
    assert payload.message == "Query processed successfully"
    assert set(payload.data.keys()) == {"summary", "detailed_explanation", "sources"}
