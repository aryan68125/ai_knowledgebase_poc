"""Shared in-memory index store for ingestion and retrieval layers."""

from __future__ import annotations

from typing import Any

from app.core.logger import ATHENA_LOGGER


class InMemoryIndexStore:
    """Thread-local process in-memory store for indexed chunk payloads."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def upsert_many(self, records: list[dict[str, Any]]) -> int:
        """Upsert chunk records keyed by `chunk_id`."""

        try:
            ATHENA_LOGGER.info(
                module="app.core.index_store",
                class_name="InMemoryIndexStore",
                method="upsert_many",
                message="Index store upsert started",
                extra={"incoming_records": len(records)},
            )
            for record in records:
                chunk_id = str(record.get("chunk_id", ""))
                if not chunk_id:
                    continue
                self._records[chunk_id] = record
            current_size = len(self._records)
            ATHENA_LOGGER.info(
                module="app.core.index_store",
                class_name="InMemoryIndexStore",
                method="upsert_many",
                message="Index store upsert completed",
                extra={"incoming_records": len(records), "current_size": current_size},
            )
            return current_size
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.index_store",
                class_name="InMemoryIndexStore",
                method="upsert_many",
                message="Index store upsert failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[InMemoryIndexStore.upsert_many] {str(exc)}") from exc

    def all_records(self) -> list[dict[str, Any]]:
        """Return all indexed records."""

        try:
            records = list(self._records.values())
            ATHENA_LOGGER.debug(
                module="app.core.index_store",
                class_name="InMemoryIndexStore",
                method="all_records",
                message="Index store records requested",
                extra={"records_count": len(records)},
            )
            return records
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.index_store",
                class_name="InMemoryIndexStore",
                method="all_records",
                message="Index store read failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[InMemoryIndexStore.all_records] {str(exc)}") from exc

    def size(self) -> int:
        """Return current index size."""

        try:
            current_size = len(self._records)
            ATHENA_LOGGER.debug(
                module="app.core.index_store",
                class_name="InMemoryIndexStore",
                method="size",
                message="Index store size requested",
                extra={"current_size": current_size},
            )
            return current_size
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.index_store",
                class_name="InMemoryIndexStore",
                method="size",
                message="Index store size failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[InMemoryIndexStore.size] {str(exc)}") from exc

    def clear(self) -> None:
        """Clear all indexed records."""

        try:
            cleared_size = len(self._records)
            self._records.clear()
            ATHENA_LOGGER.info(
                module="app.core.index_store",
                class_name="InMemoryIndexStore",
                method="clear",
                message="Index store cleared",
                extra={"cleared_records": cleared_size},
            )
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.core.index_store",
                class_name="InMemoryIndexStore",
                method="clear",
                message="Index store clear failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[InMemoryIndexStore.clear] {str(exc)}") from exc


INDEX_STORE = InMemoryIndexStore()
