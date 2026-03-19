"""Hugging Face chat-completion client for DeepSeek answer generation."""

from __future__ import annotations

import json
from typing import Any, Protocol
from urllib import request

from app.core.config import SETTINGS, Settings
from app.core.logger import ATHENA_LOGGER


class _JsonHttpTransport(Protocol):
    """Transport contract for JSON POST APIs."""

    def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        """Send JSON payload and parse JSON response."""


class _UrllibJsonHttpTransport:
    """urllib-backed JSON transport used for Hugging Face API requests."""

    def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        """POST JSON payload and decode JSON body."""

        try:
            ATHENA_LOGGER.debug(
                module="app.core.huggingface_client",
                class_name="_UrllibJsonHttpTransport",
                method="post_json",
                message="JSON POST request started",
                extra={"url": url, "timeout_seconds": timeout_seconds},
            )
            raw_payload = json.dumps(payload).encode("utf-8")
            http_request = request.Request(
                url=url,
                headers=headers,
                data=raw_payload,
                method="POST",
            )
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                decoded = json.loads(response.read().decode("utf-8"))
            ATHENA_LOGGER.debug(
                module="app.core.huggingface_client",
                class_name="_UrllibJsonHttpTransport",
                method="post_json",
                message="JSON POST request completed",
                extra={"url": url},
            )
            return decoded
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.huggingface_client",
                class_name="_UrllibJsonHttpTransport",
                method="post_json",
                message="JSON POST request failed",
                extra={"url": url, "error": str(exc)},
            )
            raise Exception(f"[_UrllibJsonHttpTransport.post_json] {str(exc)}") from exc


class HuggingFaceChatClient:
    """Client to call Hugging Face chat completion endpoint."""

    def __init__(
        self,
        settings: Settings | None = None,
        transport: _JsonHttpTransport | None = None,
    ) -> None:
        self._settings = settings or SETTINGS
        self._transport = transport or _UrllibJsonHttpTransport()

    def generate_answer(self, query: str, context_chunks: list[str]) -> str:
        """Generate answer text from query + context chunks using DeepSeek-R1."""

        try:
            ATHENA_LOGGER.info(
                module="app.core.huggingface_client",
                class_name="HuggingFaceChatClient",
                method="generate_answer",
                message="Hugging Face answer generation started",
                extra={
                    "model_id": self._settings.hf_model_id,
                    "context_chunks": len(context_chunks),
                },
            )
            if not self._settings.hf_api_token.strip():
                raise ValueError("HF_API_TOKEN is required for Hugging Face API calls")

            context_block = "\n\n".join(context_chunks)
            user_message = (
                "Use ONLY the context below to answer the question.\n"
                "If context is insufficient, explicitly say you do not know.\n"
                "Return JSON with keys: summary, detailed_explanation.\n\n"
                "Output must be raw JSON only (no markdown fences, no <think> tags, "
                "and no extra commentary).\n\n"
                f"Question:\n{query}\n\n"
                f"Context:\n{context_block}"
            )
            payload: dict[str, Any] = {
                "model": self._settings.hf_model_id,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a retrieval-grounded assistant. "
                            "Do not invent facts outside supplied context."
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": self._settings.hf_max_tokens,
                "temperature": self._settings.hf_temperature,
                "stream": False,
            }
            response = self._transport.post_json(
                url=self._settings.hf_chat_completion_url,
                headers={
                    "Authorization": f"Bearer {self._settings.hf_api_token}",
                    "Content-Type": "application/json",
                },
                payload=payload,
                timeout_seconds=self._settings.hf_timeout_seconds,
            )

            choices = response.get("choices", [])
            if not isinstance(choices, list) or not choices:
                raise ValueError("Hugging Face response did not include choices")

            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                raise ValueError("Hugging Face response choice has invalid shape")

            message_payload = first_choice.get("message", {})
            if not isinstance(message_payload, dict):
                raise ValueError("Hugging Face response message has invalid shape")

            content = str(message_payload.get("content", "")).strip()
            if not content:
                raise ValueError("Hugging Face response content is empty")

            ATHENA_LOGGER.info(
                module="app.core.huggingface_client",
                class_name="HuggingFaceChatClient",
                method="generate_answer",
                message="Hugging Face answer generation completed",
                extra={"content_length": len(content)},
            )
            return content
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.huggingface_client",
                class_name="HuggingFaceChatClient",
                method="generate_answer",
                message="Hugging Face answer generation failed",
                extra={"error": str(exc), "model_id": self._settings.hf_model_id},
            )
            raise Exception(f"[HuggingFaceChatClient.generate_answer] {str(exc)}") from exc
