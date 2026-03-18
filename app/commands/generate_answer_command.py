"""Command for deterministic answer generation from retrieved context."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.commands.base_command import BaseCommand
from app.core.logger import ATHENA_LOGGER
from app.models.query_models import RetrievalChunk
from app.models.response_models import QueryAnswer


class GenerateAnswerInput(BaseModel):
    """Input contract for answer generation."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    retrieved_chunks: list[RetrievalChunk]


class GenerateAnswerCommand(BaseCommand[GenerateAnswerInput, QueryAnswer]):
    """Create deterministic answers from retrieval output only."""

    def execute(self, input_model: GenerateAnswerInput) -> QueryAnswer:
        """Build an answer strictly from retrieved context chunks."""

        try:
            ATHENA_LOGGER.info(
                module="app.commands.generate_answer_command",
                class_name="GenerateAnswerCommand",
                method="execute",
                message="Answer generation command started",
                extra={
                    "query": input_model.query,
                    "retrieved_chunks": len(input_model.retrieved_chunks),
                },
            )
            if not input_model.retrieved_chunks:
                ATHENA_LOGGER.warning(
                    module="app.commands.generate_answer_command",
                    class_name="GenerateAnswerCommand",
                    method="execute",
                    message="No retrieval evidence found for answer generation",
                    extra={"query": input_model.query},
                )
                response = QueryAnswer(
                    summary="I don't know based on available information",
                    detailed_explanation=(
                        "No relevant retrieved sources were available to answer the query."
                    ),
                    sources=[],
                )
                ATHENA_LOGGER.info(
                    module="app.commands.generate_answer_command",
                    class_name="GenerateAnswerCommand",
                    method="execute",
                    message="Answer generation command completed",
                    extra={"query": input_model.query, "sources_count": 0},
                )
                return response

            source_lines: list[str] = []
            detail_lines: list[str] = []
            for index, chunk in enumerate(input_model.retrieved_chunks, start=1):
                citation: str = f"[{index}]"
                source_lines.append(f"{citation} {chunk.source_name}")
                detail_lines.append(f"{citation} {chunk.excerpt}")

            response = QueryAnswer(
                summary="Answer generated from retrieved internal sources",
                detailed_explanation="\n".join(detail_lines),
                sources=source_lines,
            )
            ATHENA_LOGGER.info(
                module="app.commands.generate_answer_command",
                class_name="GenerateAnswerCommand",
                method="execute",
                message="Answer generation command completed",
                extra={"query": input_model.query, "sources_count": len(source_lines)},
            )
            return response
        except Exception as exc:  # pragma: no cover - defensive boundary
            ATHENA_LOGGER.error(
                module="app.commands.generate_answer_command",
                class_name="GenerateAnswerCommand",
                method="execute",
                message="Answer generation command failed",
                extra={"query": input_model.query, "error": str(exc)},
            )
            raise Exception(f"[GenerateAnswerCommand.execute] {str(exc)}") from exc
