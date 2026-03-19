"""Deterministic text embedder used for local vector database indexing/query."""

from __future__ import annotations

import hashlib
import math
import re

from app.core.config import SETTINGS
from app.core.logger import ATHENA_LOGGER


class HashTokenEmbedder:
    """Generate deterministic dense vectors using a token hashing trick."""

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


TEXT_EMBEDDER = HashTokenEmbedder(dimension=SETTINGS.vector_db_dimension)
