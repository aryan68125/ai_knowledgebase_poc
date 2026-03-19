"""Vector store abstractions and provider implementations."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5
from pathlib import Path
from typing import Any, Protocol

from app.core.config import SETTINGS, Settings
from app.core.logger import ATHENA_LOGGER


class VectorStoreProtocol(Protocol):
    """Vector store contract for indexing and retrieval layers."""

    @property
    def index_name(self) -> str:
        """Return configured index/collection name."""

    def upsert_many(self, records: list[dict[str, Any]], vectors: list[list[float]]) -> int:
        """Upsert vectors and metadata records; return total stored size."""

    def query(self, vector: list[float], top_k: int) -> list[dict[str, Any]]:
        """Query nearest vectors and return payload records."""

    def size(self) -> int:
        """Return total number of vectors in the index."""

    def clear(self) -> None:
        """Delete all vectors from the index."""


class InMemoryVectorStore:
    """In-memory vector store provider used as fallback provider."""

    def __init__(self, index_name: str) -> None:
        self._index_name = index_name
        self._records: dict[str, dict[str, Any]] = {}
        self._vectors: dict[str, list[float]] = {}

    @property
    def index_name(self) -> str:
        """Return in-memory index name."""

        return self._index_name

    def upsert_many(self, records: list[dict[str, Any]], vectors: list[list[float]]) -> int:
        """Upsert vectors and payload records into in-memory dictionaries."""

        try:
            ATHENA_LOGGER.info(
                module="app.core.vector_store",
                class_name="InMemoryVectorStore",
                method="upsert_many",
                message="In-memory vector upsert started",
                extra={"incoming_records": len(records), "index_name": self._index_name},
            )
            for record, vector in zip(records, vectors, strict=False):
                chunk_id = str(record.get("chunk_id", "")).strip()
                if not chunk_id:
                    continue
                self._records[chunk_id] = record
                self._vectors[chunk_id] = vector

            current_size = len(self._records)
            ATHENA_LOGGER.info(
                module="app.core.vector_store",
                class_name="InMemoryVectorStore",
                method="upsert_many",
                message="In-memory vector upsert completed",
                extra={"current_size": current_size, "index_name": self._index_name},
            )
            return current_size
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.vector_store",
                class_name="InMemoryVectorStore",
                method="upsert_many",
                message="In-memory vector upsert failed",
                extra={"error": str(exc), "index_name": self._index_name},
            )
            raise Exception(f"[InMemoryVectorStore.upsert_many] {str(exc)}") from exc

    def query(self, vector: list[float], top_k: int) -> list[dict[str, Any]]:
        """Return top-k payload records by cosine similarity."""

        try:
            ATHENA_LOGGER.debug(
                module="app.core.vector_store",
                class_name="InMemoryVectorStore",
                method="query",
                message="In-memory vector query started",
                extra={"top_k": top_k, "index_name": self._index_name},
            )
            scored: list[tuple[float, str]] = []
            for chunk_id, stored_vector in self._vectors.items():
                score = _cosine_similarity(vector, stored_vector)
                scored.append((score, chunk_id))

            scored.sort(key=lambda item: item[0], reverse=True)
            result = [self._records[chunk_id] for _, chunk_id in scored[:top_k]]
            ATHENA_LOGGER.debug(
                module="app.core.vector_store",
                class_name="InMemoryVectorStore",
                method="query",
                message="In-memory vector query completed",
                extra={"returned_records": len(result), "index_name": self._index_name},
            )
            return result
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.vector_store",
                class_name="InMemoryVectorStore",
                method="query",
                message="In-memory vector query failed",
                extra={"error": str(exc), "index_name": self._index_name},
            )
            raise Exception(f"[InMemoryVectorStore.query] {str(exc)}") from exc

    def size(self) -> int:
        """Return count of stored vectors."""

        return len(self._records)

    def clear(self) -> None:
        """Clear in-memory vector store content."""

        self._records.clear()
        self._vectors.clear()
        ATHENA_LOGGER.info(
            module="app.core.vector_store",
            class_name="InMemoryVectorStore",
            method="clear",
            message="In-memory vector store cleared",
            extra={"index_name": self._index_name},
        )


class QdrantLocalVectorStore:
    """Qdrant local-mode vector store persisted on local filesystem."""

    def __init__(self, collection_name: str, path: str, vector_size: int) -> None:
        self._collection_name = collection_name
        self._path = path
        self._vector_size = vector_size

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams

            Path(path).mkdir(parents=True, exist_ok=True)
            self._client = QdrantClient(path=path)
            self._distance = Distance
            self._vector_params = VectorParams
            self._ensure_collection()
            ATHENA_LOGGER.info(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="__init__",
                message="Qdrant local vector store initialized",
                extra={
                    "collection_name": self._collection_name,
                    "path": self._path,
                    "vector_size": self._vector_size,
                },
            )
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="__init__",
                message="Qdrant local vector store initialization failed",
                extra={
                    "error": str(exc),
                    "collection_name": self._collection_name,
                    "path": self._path,
                },
            )
            raise Exception(f"[QdrantLocalVectorStore.__init__] {str(exc)}") from exc

    @property
    def index_name(self) -> str:
        """Return Qdrant collection name."""

        return self._collection_name

    def upsert_many(self, records: list[dict[str, Any]], vectors: list[list[float]]) -> int:
        """Upsert records into Qdrant collection and return collection size."""

        try:
            from qdrant_client.http.models import PointStruct

            ATHENA_LOGGER.info(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="upsert_many",
                message="Qdrant vector upsert started",
                extra={"incoming_records": len(records), "collection_name": self._collection_name},
            )
            points: list[PointStruct] = []
            for record, vector in zip(records, vectors, strict=False):
                chunk_id = str(record.get("chunk_id", "")).strip()
                if not chunk_id:
                    continue
                point_id = self._build_point_id(chunk_id=chunk_id)
                points.append(PointStruct(id=point_id, vector=vector, payload=record))

            if points:
                self._client.upsert(
                    collection_name=self._collection_name,
                    points=points,
                    wait=True,
                )

            current_size = self.size()
            ATHENA_LOGGER.info(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="upsert_many",
                message="Qdrant vector upsert completed",
                extra={"current_size": current_size, "collection_name": self._collection_name},
            )
            return current_size
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="upsert_many",
                message="Qdrant vector upsert failed",
                extra={"error": str(exc), "collection_name": self._collection_name},
            )
            raise Exception(f"[QdrantLocalVectorStore.upsert_many] {str(exc)}") from exc

    def query(self, vector: list[float], top_k: int) -> list[dict[str, Any]]:
        """Query Qdrant by vector and return payload records."""

        try:
            ATHENA_LOGGER.debug(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="query",
                message="Qdrant vector query started",
                extra={"top_k": top_k, "collection_name": self._collection_name},
            )
            scored_points = self._query_points(vector=vector, top_k=top_k)

            payloads: list[dict[str, Any]] = []
            for point in scored_points:
                payload = getattr(point, "payload", None)
                if isinstance(payload, dict):
                    payloads.append(payload)

            ATHENA_LOGGER.debug(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="query",
                message="Qdrant vector query completed",
                extra={"returned_records": len(payloads), "collection_name": self._collection_name},
            )
            return payloads
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="query",
                message="Qdrant vector query failed",
                extra={"error": str(exc), "collection_name": self._collection_name},
            )
            raise Exception(f"[QdrantLocalVectorStore.query] {str(exc)}") from exc

    def _query_points(self, vector: list[float], top_k: int) -> list[Any]:
        """Run vector search across Qdrant client API variants."""

        if hasattr(self._client, "query_points"):
            ATHENA_LOGGER.debug(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="_query_points",
                message="Querying Qdrant using query_points API",
                extra={"collection_name": self._collection_name, "top_k": top_k},
            )
            response = self._client.query_points(
                collection_name=self._collection_name,
                query=vector,
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )
            points = getattr(response, "points", None)
            if isinstance(points, list):
                ATHENA_LOGGER.debug(
                    module="app.core.vector_store",
                    class_name="QdrantLocalVectorStore",
                    method="_query_points",
                    message="Qdrant query_points API returned candidates",
                    extra={
                        "collection_name": self._collection_name,
                        "returned_points": len(points),
                    },
                )
                return points
            return []

        # Backward-compatible fallback for older qdrant-client versions.
        ATHENA_LOGGER.debug(
            module="app.core.vector_store",
            class_name="QdrantLocalVectorStore",
            method="_query_points",
            message="Querying Qdrant using legacy search API fallback",
            extra={"collection_name": self._collection_name, "top_k": top_k},
        )
        return self._client.search(  # pragma: no cover - compatibility branch
            collection_name=self._collection_name,
            query_vector=vector,
            limit=top_k,
            with_payload=True,
        )

    def size(self) -> int:
        """Return Qdrant collection vector count."""

        try:
            result = self._client.count(collection_name=self._collection_name, exact=True)
            return int(getattr(result, "count", 0))
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="size",
                message="Failed to read Qdrant collection size",
                extra={"error": str(exc), "collection_name": self._collection_name},
            )
            raise Exception(f"[QdrantLocalVectorStore.size] {str(exc)}") from exc

    def clear(self) -> None:
        """Drop and recreate collection to clear all vectors."""

        try:
            ATHENA_LOGGER.info(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="clear",
                message="Qdrant vector store clear started",
                extra={"collection_name": self._collection_name},
            )
            try:
                self._client.delete_collection(collection_name=self._collection_name)
            except Exception:
                ATHENA_LOGGER.debug(
                    module="app.core.vector_store",
                    class_name="QdrantLocalVectorStore",
                    method="clear",
                    message="Qdrant collection delete skipped (collection may not exist)",
                    extra={"collection_name": self._collection_name},
                )
            self._ensure_collection()
            ATHENA_LOGGER.info(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="clear",
                message="Qdrant vector store clear completed",
                extra={"collection_name": self._collection_name},
            )
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="clear",
                message="Qdrant vector store clear failed",
                extra={"error": str(exc), "collection_name": self._collection_name},
            )
            raise Exception(f"[QdrantLocalVectorStore.clear] {str(exc)}") from exc

    def _ensure_collection(self) -> None:
        """Create collection if it does not exist."""

        try:
            collection_exists = self._collection_exists()
            if collection_exists:
                return
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=self._vector_params(
                    size=self._vector_size,
                    distance=self._distance.COSINE,
                ),
            )
            ATHENA_LOGGER.info(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="_ensure_collection",
                message="Created Qdrant collection",
                extra={
                    "collection_name": self._collection_name,
                    "vector_size": self._vector_size,
                },
            )
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.vector_store",
                class_name="QdrantLocalVectorStore",
                method="_ensure_collection",
                message="Failed to ensure Qdrant collection",
                extra={"error": str(exc), "collection_name": self._collection_name},
            )
            raise Exception(f"[QdrantLocalVectorStore._ensure_collection] {str(exc)}") from exc

    def _collection_exists(self) -> bool:
        """Return whether the Qdrant collection currently exists."""

        try:
            return bool(self._client.collection_exists(self._collection_name))
        except Exception:
            try:
                self._client.get_collection(self._collection_name)
                return True
            except Exception:
                return False

    @staticmethod
    def _build_point_id(chunk_id: str) -> str:
        """Build deterministic UUID point ID for Qdrant compatibility."""

        return str(uuid5(NAMESPACE_URL, chunk_id))


def build_vector_store(settings: Settings) -> VectorStoreProtocol:
    """Build active vector store provider from settings."""

    provider = settings.vector_db_provider.lower()
    try:
        ATHENA_LOGGER.info(
            module="app.core.vector_store",
            class_name="VectorStoreFactory",
            method="build_vector_store",
            message="Building vector store provider",
            extra={"provider": provider},
        )
        if provider == "qdrant_local":
            return QdrantLocalVectorStore(
                collection_name=settings.vector_db_collection_name,
                path=settings.vector_db_path,
                vector_size=settings.vector_db_dimension,
            )

        return InMemoryVectorStore(index_name="knowledgebase_inmemory_vectors")
    except Exception as exc:
        ATHENA_LOGGER.warning(
            module="app.core.vector_store",
            class_name="VectorStoreFactory",
            method="build_vector_store",
            message="Vector store provider init failed; using in-memory fallback",
            extra={"provider": provider, "error": str(exc)},
        )
        return InMemoryVectorStore(index_name="knowledgebase_inmemory_vectors")


def _cosine_similarity(lhs: list[float], rhs: list[float]) -> float:
    """Compute cosine similarity between equal-length vectors."""

    if not lhs or not rhs or len(lhs) != len(rhs):
        return 0.0

    dot = sum(a * b for a, b in zip(lhs, rhs, strict=False))
    lhs_norm = sum(a * a for a in lhs) ** 0.5
    rhs_norm = sum(b * b for b in rhs) ** 0.5
    if lhs_norm == 0.0 or rhs_norm == 0.0:
        return 0.0
    return dot / (lhs_norm * rhs_norm)


VECTOR_STORE: VectorStoreProtocol = build_vector_store(settings=SETTINGS)
