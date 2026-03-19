"""Text embedder implementations for local vector database indexing and query."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

import httpx

from app.core.config import SETTINGS, Settings
from app.core.logger import ATHENA_LOGGER


class HashTokenEmbedder:
    """Generate deterministic dense vectors using a token hashing trick.

    Used as a fallback when no real embedding model is configured.
    """

    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        """Return embedding vector dimensionality."""

        return self._dimension

    def embed(self, text: str) -> list[float]:
        """Embed text into a normalized dense vector."""

        try:
            ATHENA_LOGGER.debug(
                module="app.core.text_embedder",
                class_name="HashTokenEmbedder",
                method="embed",
                message="Embedding generation started",
                extra={"text_length": len(text), "dimension": self._dimension},
            )

            tokens = self._tokenize(text)
            vector = [0.0] * self._dimension
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], byteorder="big") % self._dimension
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[index] += sign

            normalized_vector = self._l2_normalize(vector)
            ATHENA_LOGGER.debug(
                module="app.core.text_embedder",
                class_name="HashTokenEmbedder",
                method="embed",
                message="Embedding generation completed",
                extra={"token_count": len(tokens), "dimension": self._dimension},
            )
            return normalized_vector
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.text_embedder",
                class_name="HashTokenEmbedder",
                method="embed",
                message="Embedding generation failed",
                extra={"error": str(exc), "dimension": self._dimension},
            )
            raise Exception(f"[HashTokenEmbedder.embed] {str(exc)}") from exc

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase alphanumeric terms."""

        return re.findall(r"[a-zA-Z0-9]+", text.lower())

    @staticmethod
    def _l2_normalize(vector: list[float]) -> list[float]:
        """L2-normalize vector; return as-is for zero norm."""

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


class HuggingFaceEmbedder:
    """Generate semantic embeddings via the HuggingFace Inference API.

    Uses ``sentence-transformers/all-MiniLM-L6-v2`` by default, producing
    384-dimensional vectors that are drop-in compatible with the existing
    Qdrant collection configuration.
    """

    def __init__(self, api_token: str, model_url: str, model_id: str, timeout: int = 60) -> None:
        self._api_token = api_token
        self._model_url = model_url
        self._model_id = model_id
        self._timeout = timeout

    @property
    def dimension(self) -> int:
        """Return expected output dimension (384 for all-MiniLM-L6-v2)."""

        return 384

    def embed(self, text: str) -> list[float]:
        """Embed a single text by calling the HuggingFace Inference API."""

        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Embed multiple texts in batches, reducing the number of API calls.

        Sends up to ``batch_size`` texts per request.
        ``{"inputs": ["text1", "text2", ...]}`` → ``[[vec1], [vec2], ...]``
        """

        all_vectors: list[list[float]] = []

        for batch_start in range(0, len(texts), batch_size):
            batch = texts[batch_start : batch_start + batch_size]
            try:
                ATHENA_LOGGER.debug(
                    module="app.core.text_embedder",
                    class_name="HuggingFaceEmbedder",
                    method="embed_many",
                    message="HuggingFace batch embedding started",
                    extra={
                        "model_id": self._model_id,
                        "batch_size": len(batch),
                        "batch_start": batch_start,
                    },
                )

                response = httpx.post(
                    url=self._model_url,
                    headers={
                        "Authorization": f"Bearer {self._api_token}",
                        "Content-Type": "application/json",
                    },
                    json={"inputs": batch},
                    timeout=self._timeout,
                )
                response.raise_for_status()

                payload: Any = response.json()
                batch_vectors = self._parse_batch_vectors(payload, expected_count=len(batch))
                all_vectors.extend(batch_vectors)

                ATHENA_LOGGER.debug(
                    module="app.core.text_embedder",
                    class_name="HuggingFaceEmbedder",
                    method="embed_many",
                    message="HuggingFace batch embedding completed",
                    extra={"model_id": self._model_id, "vectors_returned": len(batch_vectors)},
                )

            except Exception as exc:
                ATHENA_LOGGER.error(
                    module="app.core.text_embedder",
                    class_name="HuggingFaceEmbedder",
                    method="embed_many",
                    message="HuggingFace batch embedding failed",
                    extra={"model_id": self._model_id, "error": str(exc), "batch_start": batch_start},
                )
                raise Exception(f"[HuggingFaceEmbedder.embed_many] {str(exc)}") from exc

        return all_vectors

    @staticmethod
    def _parse_batch_vectors(payload: Any, expected_count: int) -> list[list[float]]:
        """Parse batch response: list of embedding vectors, one per input text.

        The /pipeline/feature-extraction endpoint returns ``[[v1, v2, ...], [v1, v2, ...]]``
        when given a list of inputs.
        """

        if (
            isinstance(payload, list)
            and len(payload) == expected_count
            and all(isinstance(row, list) for row in payload)
        ):
            return [[float(v) for v in row] for row in payload]

        raise ValueError(
            f"Unexpected batch embedding response shape — "
            f"expected list of {expected_count} vectors, got: {type(payload)}"
        )


    @staticmethod
    def _parse_vector(payload: Any) -> list[float]:
        """Extract flat float list from HF Inference API response.

        Handles the response shapes returned by /pipeline/feature-extraction:
        - Primary (confirmed): flat ``[v1, v2, ...]`` list of floats
        - Legacy wrapped: ``[[v1, v2, ...]]`` (outer list with single embedding)
        - OpenAI-compatible: ``{"data": [{"embedding": [...]}]}``
        """

        # Primary: flat list of floats (confirmed from /pipeline/feature-extraction).
        if (
            isinstance(payload, list)
            and payload
            and isinstance(payload[0], (int, float))
        ):
            return [float(v) for v in payload]

        # Legacy wrapped: [[float, ...]] returned by some HF API versions.
        if (
            isinstance(payload, list)
            and len(payload) == 1
            and isinstance(payload[0], list)
            and payload[0]
            and isinstance(payload[0][0], (int, float))
        ):
            return [float(v) for v in payload[0]]

        # OpenAI-compatible router format: {"data": [{"embedding": [...]}]}.
        if isinstance(payload, dict) and "data" in payload:
            data = payload["data"]
            if (
                isinstance(data, list)
                and data
                and isinstance(data[0], dict)
                and "embedding" in data[0]
            ):
                return [float(v) for v in data[0]["embedding"]]

        raise ValueError(
            f"Unexpected HuggingFace embedding response shape: {type(payload)}"
        )


def build_text_embedder(settings: Settings) -> HuggingFaceEmbedder | HashTokenEmbedder:
    """Build the active text embedder from settings.

    Returns ``HuggingFaceEmbedder`` when ``HF_API_TOKEN`` is configured,
    otherwise falls back to ``HashTokenEmbedder`` with a logged warning.
    """

    if settings.hf_api_token:
        ATHENA_LOGGER.info(
            module="app.core.text_embedder",
            class_name="EmbedderFactory",
            method="build_text_embedder",
            message="Using HuggingFace Inference API embedder",
            extra={"model_id": settings.hf_embedding_model_id},
        )
        return HuggingFaceEmbedder(
            api_token=settings.hf_api_token,
            model_url=settings.hf_embedding_url,
            model_id=settings.hf_embedding_model_id,
        )

    ATHENA_LOGGER.warning(
        module="app.core.text_embedder",
        class_name="EmbedderFactory",
        method="build_text_embedder",
        message=(
            "HF_API_TOKEN is not set — falling back to HashTokenEmbedder. "
            "Set HF_API_TOKEN in .env to enable semantic embeddings."
        ),
        extra={"fallback": "HashTokenEmbedder", "dimension": settings.vector_db_dimension},
    )
    return HashTokenEmbedder(dimension=settings.vector_db_dimension)


TEXT_EMBEDDER: HuggingFaceEmbedder | HashTokenEmbedder = build_text_embedder(settings=SETTINGS)
