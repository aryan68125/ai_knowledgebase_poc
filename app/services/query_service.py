"""Query service orchestrating retrieval and answer command execution."""

from __future__ import annotations

from fastapi import status

from app.commands.generate_answer_command import GenerateAnswerCommand, GenerateAnswerInput
from app.core.logger import ATHENA_LOGGER
from app.models.query_models import RetrievalRequest
from app.models.response_models import BaseResponse
from app.rag.retriever import Retriever


class QueryService:
    """Service layer orchestration for query answering."""

    def __init__(
        self,
        retriever: Retriever | None = None,
        answer_command: GenerateAnswerCommand | None = None,
    ) -> None:
        self._retriever: Retriever = retriever or Retriever()
        self._answer_command: GenerateAnswerCommand = answer_command or GenerateAnswerCommand()

    def answer_user_query(self, query: str) -> BaseResponse:
        """Run retrieval-first pipeline and return standardized response envelope."""

        try:
            ATHENA_LOGGER.info(
                module="app.services.query_service",
                class_name="QueryService",
                method="answer_user_query",
                message="Query service execution started",
                extra={"query": query},
            )
            retrieval_result = self._retriever.retrieve(RetrievalRequest(query=query))
            ATHENA_LOGGER.info(
                module="app.services.query_service",
                class_name="QueryService",
                method="answer_user_query",
                message="Retrieval step completed",
                extra={"query": query, "retrieved_chunks": len(retrieval_result.chunks)},
            )
            answer = self._answer_command.execute(
                GenerateAnswerInput(query=query, retrieved_chunks=retrieval_result.chunks)
            )

            response = BaseResponse(
                status=status.HTTP_200_OK,
                message="Query processed successfully",
                data={
                    "summary": answer.summary,
                    "detailed_explanation": answer.detailed_explanation,
                    "sources": answer.sources,
                },
            )
            ATHENA_LOGGER.info(
                module="app.services.query_service",
                class_name="QueryService",
                method="answer_user_query",
                message="Query service execution completed",
                status_code=response.status,
                extra={"query": query, "sources_count": len(answer.sources)},
            )
            return response
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.services.query_service",
                class_name="QueryService",
                method="answer_user_query",
                message="Query service execution failed",
                extra={"query": query, "error": str(exc)},
            )
            raise Exception(f"[QueryService.answer_user_query] {str(exc)}") from exc
