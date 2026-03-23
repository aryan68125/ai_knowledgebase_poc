"""Hugging Face chat-completion client for DeepSeek answer generation."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Protocol

import httpx

from app.core.config import SETTINGS, Settings
from app.core.logger import ATHENA_LOGGER

_RETRYABLE_STATUS_CODES = {429, 503}
_MAX_RETRIES = 3
_RETRY_INITIAL_WAIT_SECONDS = 5


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
    """httpx-backed JSON transport with retry/backoff for 429 and 503 responses."""

    def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        """POST JSON payload and decode JSON body. Retries on 429/503 with exponential backoff."""

        last_exc: Exception | None = None
        wait = _RETRY_INITIAL_WAIT_SECONDS

        for attempt in range(1, _MAX_RETRIES + 2):  # attempts: 1..4 (3 retries + 1 final)
            try:
                ATHENA_LOGGER.debug(
                    module="app.core.huggingface_client",
                    class_name="_UrllibJsonHttpTransport",
                    method="post_json",
                    message="JSON POST request started",
                    extra={"url": url, "timeout_seconds": timeout_seconds, "attempt": attempt},
                )
                response = httpx.post(
                    url=url,
                    headers=headers,
                    json=payload,
                    timeout=timeout_seconds,
                )

                if response.status_code in _RETRYABLE_STATUS_CODES and attempt <= _MAX_RETRIES:
                    ATHENA_LOGGER.warning(
                        module="app.core.huggingface_client",
                        class_name="_UrllibJsonHttpTransport",
                        method="post_json",
                        message=(
                            f"Hugging Face API returned {response.status_code} "
                            f"(attempt {attempt}/{_MAX_RETRIES}). "
                            f"Retrying in {wait}s..."
                        ),
                        extra={"url": url, "status_code": response.status_code, "wait_seconds": wait},
                    )
                    time.sleep(wait)
                    wait *= 2
                    continue

                response.raise_for_status()
                decoded: dict[str, Any] = response.json()
                ATHENA_LOGGER.debug(
                    module="app.core.huggingface_client",
                    class_name="_UrllibJsonHttpTransport",
                    method="post_json",
                    message="JSON POST request completed",
                    extra={"url": url, "attempt": attempt},
                )
                return decoded

            except Exception as exc:
                last_exc = exc
                if attempt <= _MAX_RETRIES:
                    ATHENA_LOGGER.warning(
                        module="app.core.huggingface_client",
                        class_name="_UrllibJsonHttpTransport",
                        method="post_json",
                        message=(
                            f"JSON POST request failed on attempt {attempt}/{_MAX_RETRIES}. "
                            f"Retrying in {wait}s..."
                        ),
                        extra={"url": url, "error": str(exc), "wait_seconds": wait},
                    )
                    time.sleep(wait)
                    wait *= 2
                else:
                    ATHENA_LOGGER.error(
                        module="app.core.huggingface_client",
                        class_name="_UrllibJsonHttpTransport",
                        method="post_json",
                        message="JSON POST request failed after all retries",
                        extra={"url": url, "error": str(exc), "attempts": _MAX_RETRIES},
                    )

        cause = last_exc if isinstance(last_exc, BaseException) else RuntimeError(str(last_exc))
        raise Exception(f"[_UrllibJsonHttpTransport.post_json] {str(last_exc)}") from cause


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
                            "You are a highly precise, retrieval-grounded assistant. "
                            "Do not invent facts outside supplied context. "
                            "Your answers MUST be extremely short, precise, and accurate. "
                            "Provide the exact requested numerical answer or factual statement in 1-2 sentences maximum. "
                            "Do not write expansive paragraphs."
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
                # DeepSeek-R1 on the HuggingFace router often returns an empty `content`
                # field and puts the full chain-of-thought in `reasoning_content` instead.
                # We extract the final JSON block from the reasoning text so the downstream
                # parser receives only the structured answer, not the whole monologue.
                reasoning_content = str(message_payload.get("reasoning_content", "")).strip()
                if reasoning_content:
                    extracted = self._extract_json_from_reasoning(reasoning_content)
                    ATHENA_LOGGER.info(
                        module="app.core.huggingface_client",
                        class_name="HuggingFaceChatClient",
                        method="generate_answer",
                        message="[LLM] content is empty; extracted answer from reasoning_content",
                        extra={
                            "reasoning_content_length": len(reasoning_content),
                            "extracted_length": len(extracted),
                        },
                    )
                    content = extracted
                else:
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

    @staticmethod
    def _extract_json_from_reasoning(reasoning_text: str) -> str:
        """Extract the last JSON object from DeepSeek-R1 reasoning_content.

        DeepSeek-R1 always ends its chain-of-thought reasoning with the structured
        JSON answer. We find the last '{' ... '}' block in the text and return it.
        If no valid JSON block is found we fall back to the full reasoning text so
        that the downstream _parse_llm_output can still do its best.
        """
        # Try to find the last complete {...} block in the text.
        last_brace_open = reasoning_text.rfind("{")
        last_brace_close = reasoning_text.rfind("}")
        if last_brace_open != -1 and last_brace_close > last_brace_open:
            candidate = reasoning_text[last_brace_open : last_brace_close + 1].strip()
            try:
                json.loads(candidate)  # validate it parses
                return candidate
            except Exception:
                pass  # not valid JSON; fall through

        # Fallback: look for a ```json ... ``` fenced block
        fenced = re.findall(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            reasoning_text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if fenced:
            return fenced[-1].strip()  # use the last one

        # Last resort: return the full reasoning text unchanged
        return reasoning_text
