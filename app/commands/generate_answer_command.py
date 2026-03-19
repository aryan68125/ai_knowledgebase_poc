"""Command for deterministic answer generation from retrieved context."""

from __future__ import annotations

import json
import re
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.commands.base_command import BaseCommand
from app.core.config import SETTINGS
from app.core.huggingface_client import HuggingFaceChatClient
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

    def __init__(
        self,
        hf_client: "_HuggingFaceClientProtocol | None" = None,
        hf_enabled: bool | None = None,
    ) -> None:
        self._hf_client = hf_client or HuggingFaceChatClient()
        self._hf_enabled = SETTINGS.hf_llm_enabled if hf_enabled is None else hf_enabled

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
            llm_context_chunks: list[str] = []
            for index, chunk in enumerate(input_model.retrieved_chunks, start=1):
                citation: str = f"[{index}]"
                source_lines.append(f"{citation} {chunk.source_name}")
                detail_lines.append(f"{citation} {chunk.excerpt}")
                llm_context_chunks.append(
                    f"{citation} Source: {chunk.source_name}\n{citation} Excerpt: {chunk.excerpt}"
                )

            if self._hf_enabled:
                try:
                    llm_output = self._hf_client.generate_answer(
                        query=input_model.query,
                        context_chunks=llm_context_chunks,
                    )
                    summary, detailed_explanation = self._parse_llm_output(
                        llm_output=llm_output,
                        fallback_detail_lines=detail_lines,
                    )
                    response = QueryAnswer(
                        summary=summary,
                        detailed_explanation=detailed_explanation,
                        sources=source_lines,
                    )
                    ATHENA_LOGGER.info(
                        module="app.commands.generate_answer_command",
                        class_name="GenerateAnswerCommand",
                        method="execute",
                        message="Answer generation completed with Hugging Face LLM",
                        extra={"query": input_model.query, "sources_count": len(source_lines)},
                    )
                    return response
                except Exception as llm_exc:
                    # NOTE:
                    # We intentionally keep deterministic fallback behavior so the API remains
                    # usable during local development and test runs where HF credentials may
                    # be unavailable, while still preferring DeepSeek-R1 whenever callable.
                    ATHENA_LOGGER.warning(
                        module="app.commands.generate_answer_command",
                        class_name="GenerateAnswerCommand",
                        method="execute",
                        message="Hugging Face answer generation failed; using deterministic fallback",
                        extra={"query": input_model.query, "error": str(llm_exc)},
                    )
            else:
                ATHENA_LOGGER.info(
                    module="app.commands.generate_answer_command",
                    class_name="GenerateAnswerCommand",
                    method="execute",
                    message="Hugging Face answer generation is disabled; using deterministic fallback",
                    extra={"query": input_model.query},
                )

            fallback_response = QueryAnswer(
                summary="Answer generated from retrieved internal sources",
                detailed_explanation="\n".join(detail_lines),
                sources=source_lines,
            )
            ATHENA_LOGGER.info(
                module="app.commands.generate_answer_command",
                class_name="GenerateAnswerCommand",
                method="execute",
                message="Answer generation command completed with fallback formatting",
                extra={"query": input_model.query, "sources_count": len(source_lines)},
            )
            return fallback_response
        except Exception as exc:  # pragma: no cover - defensive boundary
            ATHENA_LOGGER.error(
                module="app.commands.generate_answer_command",
                class_name="GenerateAnswerCommand",
                method="execute",
                message="Answer generation command failed",
                extra={"query": input_model.query, "error": str(exc)},
            )
            raise Exception(f"[GenerateAnswerCommand.execute] {str(exc)}") from exc

    def _parse_llm_output(
        self,
        llm_output: str,
        fallback_detail_lines: list[str],
    ) -> tuple[str, str]:
        """Parse LLM output into response contract fields."""

        cleaned_output = self._strip_reasoning_text(llm_output)
        parsed = self._extract_json_object(cleaned_output)
        if parsed is not None:
            summary = self._strip_reasoning_text(str(parsed.get("summary", ""))).strip()
            detailed_explanation = self._strip_reasoning_text(
                str(parsed.get("detailed_explanation", ""))
            ).strip()
            if summary and detailed_explanation:
                return summary, detailed_explanation

        if parsed is None:
            ATHENA_LOGGER.debug(
                module="app.commands.generate_answer_command",
                class_name="GenerateAnswerCommand",
                method="_parse_llm_output",
                message="LLM response is not strict JSON; using text fallback parser",
            )

        normalized_text = " ".join(cleaned_output.split()).strip()
        if normalized_text:
            summary = normalized_text[:220]
            return summary, cleaned_output

        return "Answer generated from retrieved internal sources", "\n".join(fallback_detail_lines)

    def _extract_json_object(self, text: str) -> dict[str, object] | None:
        """Extract best-effort JSON object from model output text."""

        for candidate in self._json_candidates(text):
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    ATHENA_LOGGER.debug(
                        module="app.commands.generate_answer_command",
                        class_name="GenerateAnswerCommand",
                        method="_extract_json_object",
                        message="Extracted JSON object from LLM output",
                    )
                    return parsed
            except Exception:
                continue
        return None

    def _json_candidates(self, text: str) -> list[str]:
        """Build candidate JSON substrings from raw response text."""

        candidates: list[str] = []
        stripped = text.strip()
        if stripped:
            candidates.append(stripped)

        fenced_blocks = re.findall(
            r"```(?:json)?\s*(.*?)\s*```",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for block in fenced_blocks:
            block_text = block.strip()
            if block_text:
                candidates.append(block_text)

        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
            brace_slice = text[first_brace : last_brace + 1].strip()
            if brace_slice:
                candidates.append(brace_slice)

        return candidates

    def _strip_reasoning_text(self, text: str) -> str:
        """Remove chain-of-thought tags and markdown fences from model output."""

        without_think = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
        without_fences = re.sub(r"```(?:json)?", "", without_think, flags=re.IGNORECASE)
        without_fences = without_fences.replace("```", "")
        return without_fences.strip()


class _HuggingFaceClientProtocol(Protocol):
    """Protocol for LLM client dependency injection in tests."""

    def generate_answer(self, query: str, context_chunks: list[str]) -> str:
        """Generate answer text from retrieval context."""
