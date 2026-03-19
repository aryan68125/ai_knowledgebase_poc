"""Tests for low-level Hugging Face chat client context and payload behavior."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.huggingface_client import HuggingFaceChatClient


class _CaptureTransport:
    """Capture request inputs and return deterministic HF-style responses."""

    def __init__(self, response: dict | None = None) -> None:
        self.response = response or {
            "choices": [{"message": {"content": '{"summary":"ok","detailed_explanation":"ok"}'}}]
        }
        self.calls = 0
        self.last_url = ""
        self.last_headers: dict[str, str] = {}
        self.last_payload: dict = {}
        self.last_timeout = 0

    def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict,
        timeout_seconds: int,
    ) -> dict:
        self.calls += 1
        self.last_url = url
        self.last_headers = headers
        self.last_payload = payload
        self.last_timeout = timeout_seconds
        return self.response


def test_hf_client_builds_payload_with_query_and_context() -> None:
    """Client should include user query and retrieval context in chat payload."""

    transport = _CaptureTransport(
        response={
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"summary":"Migration advised","detailed_explanation":"Use staged rollout"}'
                        )
                    }
                }
            ]
        }
    )
    settings = Settings().model_copy(
        update={
            "hf_api_token": "hf_test_token",
            "hf_model_id": "deepseek-ai/DeepSeek-R1",
            "hf_chat_completion_url": "https://router.huggingface.co/v1/chat/completions",
            "hf_timeout_seconds": 45,
            "hf_max_tokens": 512,
            "hf_temperature": 0.2,
        }
    )
    client = HuggingFaceChatClient(settings=settings, transport=transport)

    output = client.generate_answer(
        query="What is the migration recommendation?",
        context_chunks=[
            "[1] Source: Local Documents / proposal.docx\n[1] Excerpt: staged migration plan",
            "[2] Source: Local Chat Data / team_chat_1.json\n[2] Excerpt: cost concerns raised",
        ],
    )

    assert "Migration advised" in output
    assert transport.calls == 1
    assert transport.last_url == "https://router.huggingface.co/v1/chat/completions"
    assert transport.last_headers["Authorization"] == "Bearer hf_test_token"
    assert transport.last_payload["model"] == "deepseek-ai/DeepSeek-R1"
    assert transport.last_payload["max_tokens"] == 512
    assert transport.last_payload["temperature"] == 0.2
    user_content = transport.last_payload["messages"][1]["content"]
    assert "Question:\nWhat is the migration recommendation?" in user_content
    assert "Context:\n[1] Source: Local Documents / proposal.docx" in user_content
    assert "[2] Source: Local Chat Data / team_chat_1.json" in user_content
    assert "Output must be raw JSON only" in user_content


def test_hf_client_fails_fast_when_token_is_missing() -> None:
    """Client should reject calls when HF token is blank."""

    transport = _CaptureTransport()
    settings = Settings().model_copy(
        update={
            "hf_api_token": "",
            "hf_chat_completion_url": "https://router.huggingface.co/v1/chat/completions",
        }
    )
    client = HuggingFaceChatClient(settings=settings, transport=transport)

    with pytest.raises(Exception, match=r"\[HuggingFaceChatClient.generate_answer\]"):
        client.generate_answer(
            query="Any update?",
            context_chunks=["[1] Source: test\n[1] Excerpt: text"],
        )

    assert transport.calls == 0
