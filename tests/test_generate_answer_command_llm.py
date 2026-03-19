"""Tests for LLM-backed answer generation behavior."""

from __future__ import annotations

import json

from app.commands.generate_answer_command import GenerateAnswerCommand, GenerateAnswerInput
from app.models.enums import SourceType
from app.models.query_models import RetrievalChunk


class _StubHuggingFaceClient:
    def __init__(self, response_text: str, should_fail: bool = False) -> None:
        self._response_text = response_text
        self._should_fail = should_fail
        self.calls = 0
        self.last_query = ""
        self.last_context_chunks: list[str] = []

    def generate_answer(self, query: str, context_chunks: list[str]) -> str:
        self.calls += 1
        self.last_query = query
        self.last_context_chunks = context_chunks
        if self._should_fail:
            raise RuntimeError("simulated hf failure")
        return self._response_text


def _sample_chunks() -> list[RetrievalChunk]:
    return [
        RetrievalChunk(
            source_type=SourceType.TEAMS,
            source_name="Local Chat Data / team_chat_1.json",
            excerpt="The team discussed scaling pain and cloud cost growth.",
        ),
        RetrievalChunk(
            source_type=SourceType.SHAREPOINT,
            source_name="Local Documents / proposal.docx",
            excerpt="The proposal suggests staged microservices migration.",
        ),
    ]


def test_generate_answer_command_uses_hf_response_when_available() -> None:
    """Command should use parsed HF JSON response when API call succeeds."""

    client = _StubHuggingFaceClient(
        response_text=json.dumps(
            {
                "summary": "DeepSeek summary",
                "detailed_explanation": "DeepSeek detailed answer from static sources.",
            }
        )
    )
    command = GenerateAnswerCommand(hf_client=client)

    output = command.execute(
        GenerateAnswerInput(
            query="What is the modernization recommendation?",
            retrieved_chunks=_sample_chunks(),
        )
    )

    assert output.summary == "DeepSeek summary"
    assert output.detailed_explanation == "DeepSeek detailed answer from static sources."
    assert len(output.sources) == 2
    assert client.calls == 1


def test_generate_answer_command_falls_back_when_hf_call_fails() -> None:
    """Command should gracefully fallback to deterministic formatting on HF errors."""

    client = _StubHuggingFaceClient(response_text="", should_fail=True)
    command = GenerateAnswerCommand(hf_client=client)

    output = command.execute(
        GenerateAnswerInput(query="Summarize rollout risk", retrieved_chunks=_sample_chunks())
    )

    assert output.summary == "Answer generated from retrieved internal sources"
    assert "The team discussed scaling pain" in output.detailed_explanation
    assert len(output.sources) == 2
    assert client.calls == 1


def test_generate_answer_command_disables_hf_calls_when_flag_is_off() -> None:
    """Command should skip HF invocation entirely when hf_enabled is False."""

    client = _StubHuggingFaceClient(response_text="should-not-be-used")
    command = GenerateAnswerCommand(hf_client=client, hf_enabled=False)

    output = command.execute(
        GenerateAnswerInput(query="Summarize rollout risk", retrieved_chunks=_sample_chunks())
    )

    assert output.summary == "Answer generated from retrieved internal sources"
    assert client.calls == 0


def test_generate_answer_command_builds_citation_aware_hf_context_chunks() -> None:
    """Command should pass citation-annotated source context to HF client."""

    client = _StubHuggingFaceClient(
        response_text=json.dumps(
            {
                "summary": "Structured answer",
                "detailed_explanation": "Structured details",
            }
        )
    )
    command = GenerateAnswerCommand(hf_client=client, hf_enabled=True)

    command.execute(
        GenerateAnswerInput(
            query="What did chats and docs recommend?",
            retrieved_chunks=_sample_chunks(),
        )
    )

    assert client.calls == 1
    assert client.last_query == "What did chats and docs recommend?"
    assert len(client.last_context_chunks) == 2
    assert client.last_context_chunks[0].startswith("[1] Source: Local Chat Data / team_chat_1.json")
    assert "[1] Excerpt: The team discussed scaling pain and cloud cost growth." in client.last_context_chunks[0]
    assert client.last_context_chunks[1].startswith("[2] Source: Local Documents / proposal.docx")


def test_generate_answer_command_strips_think_and_parses_fenced_json() -> None:
    """Command should remove think/noise wrapper and parse JSON answer payload."""

    client = _StubHuggingFaceClient(
        response_text=(
            "<think>This is hidden reasoning.</think>\n"
            "```json\n"
            "{\n"
            '  "summary": "I do not know",\n'
            '  "detailed_explanation": "No cloud cost information exists in retrieved context."\n'
            "}\n"
            "```"
        )
    )
    command = GenerateAnswerCommand(hf_client=client, hf_enabled=True)

    output = command.execute(
        GenerateAnswerInput(query="What is the current cloud cost?", retrieved_chunks=_sample_chunks())
    )

    assert output.summary == "I do not know"
    assert output.detailed_explanation == "No cloud cost information exists in retrieved context."
    assert "<think>" not in output.summary
    assert "<think>" not in output.detailed_explanation
    assert "```" not in output.detailed_explanation


def test_generate_answer_command_strips_think_in_text_fallback_mode() -> None:
    """Command should clean think tags even when output is not parseable JSON."""

    client = _StubHuggingFaceClient(
        response_text=(
            "<think>Ignore this chain-of-thought.</think>\n"
            "Cloud cost cannot be determined from the provided evidence."
        )
    )
    command = GenerateAnswerCommand(hf_client=client, hf_enabled=True)

    output = command.execute(
        GenerateAnswerInput(query="What is the current cloud cost?", retrieved_chunks=_sample_chunks())
    )

    assert output.summary.startswith("Cloud cost cannot be determined")
    assert "<think>" not in output.summary
    assert "<think>" not in output.detailed_explanation
