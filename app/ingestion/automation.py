"""Automatic ingestion scheduler runtime."""

from __future__ import annotations

from threading import Event, Thread
from typing import Any

from app.core.logger import ATHENA_LOGGER
from app.ingestion.indexing_pipeline import IngestionIndexingPipeline
from app.models.enums import ConnectorMode


class IngestionScheduler:
    """Background scheduler for periodic ingestion indexing runs."""

    def __init__(
        self,
        pipeline: IngestionIndexingPipeline,
        mode: ConnectorMode,
        interval_seconds: int,
        chunk_size_tokens: int = 1000,
        chunk_overlap_tokens: int = 100,
    ) -> None:
        self._pipeline = pipeline
        self._mode = mode
        self._interval_seconds = interval_seconds
        self._chunk_size_tokens = chunk_size_tokens
        self._chunk_overlap_tokens = chunk_overlap_tokens
        self._stop_event = Event()
        self._thread: Thread | None = None

    @property
    def is_running(self) -> bool:
        """Return whether the scheduler thread is active."""

        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start scheduler thread with immediate first run."""

        try:
            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="start",
                message="Ingestion scheduler start requested",
                extra={
                    "mode": self._mode.value,
                    "interval_seconds": self._interval_seconds,
                    "is_running": self.is_running,
                },
            )
            if self.is_running:
                ATHENA_LOGGER.warning(
                    module="app.ingestion.automation",
                    class_name="IngestionScheduler",
                    method="start",
                    message="Ingestion scheduler start skipped because already running",
                    extra={"mode": self._mode.value},
                )
                return

            self._stop_event.clear()
            self._thread = Thread(
                target=self._run_loop,
                name="ingestion-scheduler",
                daemon=True,
            )
            self._thread.start()
            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="start",
                message="Ingestion scheduler started",
                extra={"mode": self._mode.value, "interval_seconds": self._interval_seconds},
            )
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="start",
                message="Ingestion scheduler failed to start",
                extra={"error": str(exc), "mode": self._mode.value},
            )
            raise Exception(f"[IngestionScheduler.start] {str(exc)}") from exc

    def stop(self) -> None:
        """Stop scheduler thread and wait briefly for termination."""

        try:
            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="stop",
                message="Ingestion scheduler stop requested",
                extra={"is_running": self.is_running, "mode": self._mode.value},
            )
            if not self.is_running:
                ATHENA_LOGGER.warning(
                    module="app.ingestion.automation",
                    class_name="IngestionScheduler",
                    method="stop",
                    message="Ingestion scheduler stop skipped because scheduler is not running",
                    extra={"mode": self._mode.value},
                )
                return

            self._stop_event.set()
            if self._thread is not None:
                self._thread.join(timeout=5)

            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="stop",
                message="Ingestion scheduler stopped",
                extra={"mode": self._mode.value},
            )
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="stop",
                message="Ingestion scheduler stop failed",
                extra={"error": str(exc), "mode": self._mode.value},
            )
            raise Exception(f"[IngestionScheduler.stop] {str(exc)}") from exc

    def run_once(self) -> Any:
        """Run ingestion pipeline once with scheduler configuration."""

        try:
            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="run_once",
                message="Ingestion scheduled run started",
                extra={
                    "mode": self._mode.value,
                    "chunk_size_tokens": self._chunk_size_tokens,
                    "chunk_overlap_tokens": self._chunk_overlap_tokens,
                },
            )
            result = self._pipeline.run(
                mode=self._mode,
                chunk_size_tokens=self._chunk_size_tokens,
                chunk_overlap_tokens=self._chunk_overlap_tokens,
            )
            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="run_once",
                message="Ingestion scheduled run completed",
                extra={
                    "mode": self._mode.value,
                    "result_status": _safe_value(result, "status"),
                    "documents_processed": _safe_value(result, "documents_processed"),
                    "chunks_indexed": _safe_value(result, "chunks_indexed"),
                },
            )
            
            print(f"\n==================================================")
            print(f"✅ INGESTION IS COMPLETED")
            print(f"   Documents Processed: {_safe_value(result, 'documents_processed')}")
            print(f"   Chunks Indexed: {_safe_value(result, 'chunks_indexed')}")
            print(f"==================================================\n")
            
            return result
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="run_once",
                message="Ingestion scheduled run failed",
                extra={"error": str(exc), "mode": self._mode.value},
            )
            raise Exception(f"[IngestionScheduler.run_once] {str(exc)}") from exc

    def _run_loop(self) -> None:
        """Loop until stop event is set, executing periodic ingestion runs."""

        try:
            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="_run_loop",
                message="Ingestion scheduler loop started",
                extra={"mode": self._mode.value, "interval_seconds": self._interval_seconds},
            )
            self._run_once_safely()
            while not self._stop_event.wait(self._interval_seconds):
                self._run_once_safely()

            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="_run_loop",
                message="Ingestion scheduler loop stopped",
                extra={"mode": self._mode.value},
            )
        except Exception as exc:  # pragma: no cover - defensive boundary
            ATHENA_LOGGER.error(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="_run_loop",
                message="Ingestion scheduler loop failed",
                extra={"error": str(exc), "mode": self._mode.value},
            )

    def _run_once_safely(self) -> None:
        """Execute one run and keep scheduler alive if the run fails."""

        try:
            self.run_once()
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.automation",
                class_name="IngestionScheduler",
                method="_run_once_safely",
                message="Ingestion scheduler run failed but loop will continue",
                extra={"error": str(exc), "mode": self._mode.value},
            )


class AutoIngestionRuntime:
    """Lifecycle wrapper for enabling/disabling scheduled ingestion."""

    def __init__(
        self,
        enabled: bool,
        mode: ConnectorMode,
        interval_seconds: int,
        pipeline: IngestionIndexingPipeline | None = None,
    ) -> None:
        self._enabled = enabled
        self._scheduler = IngestionScheduler(
            pipeline=pipeline or IngestionIndexingPipeline(),
            mode=mode,
            interval_seconds=interval_seconds,
        )

    @property
    def is_running(self) -> bool:
        """Return whether automatic ingestion scheduler is currently running."""

        return self._scheduler.is_running

    def start(self) -> None:
        """Start automatic ingestion when enabled."""

        try:
            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="AutoIngestionRuntime",
                method="start",
                message="Auto ingestion runtime start requested",
                extra={"enabled": self._enabled},
            )
            if not self._enabled:
                ATHENA_LOGGER.info(
                    module="app.ingestion.automation",
                    class_name="AutoIngestionRuntime",
                    method="start",
                    message="Auto ingestion runtime is disabled",
                    extra={"enabled": self._enabled},
                )
                return
            self._scheduler.start()
            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="AutoIngestionRuntime",
                method="start",
                message="Auto ingestion runtime started",
                extra={"enabled": self._enabled, "is_running": self.is_running},
            )
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.automation",
                class_name="AutoIngestionRuntime",
                method="start",
                message="Auto ingestion runtime failed to start",
                extra={"error": str(exc), "enabled": self._enabled},
            )
            raise Exception(f"[AutoIngestionRuntime.start] {str(exc)}") from exc

    def stop(self) -> None:
        """Stop automatic ingestion scheduler."""

        try:
            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="AutoIngestionRuntime",
                method="stop",
                message="Auto ingestion runtime stop requested",
                extra={"enabled": self._enabled, "is_running": self.is_running},
            )
            if not self._enabled:
                ATHENA_LOGGER.info(
                    module="app.ingestion.automation",
                    class_name="AutoIngestionRuntime",
                    method="stop",
                    message="Auto ingestion runtime stop skipped because runtime is disabled",
                    extra={"enabled": self._enabled},
                )
                return

            self._scheduler.stop()
            ATHENA_LOGGER.info(
                module="app.ingestion.automation",
                class_name="AutoIngestionRuntime",
                method="stop",
                message="Auto ingestion runtime stopped",
                extra={"enabled": self._enabled, "is_running": self.is_running},
            )
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.automation",
                class_name="AutoIngestionRuntime",
                method="stop",
                message="Auto ingestion runtime failed to stop",
                extra={"error": str(exc), "enabled": self._enabled},
            )
            raise Exception(f"[AutoIngestionRuntime.stop] {str(exc)}") from exc


def _safe_value(payload: Any, key: str) -> Any:
    """Read value from object/dict payloads for structured logging extras."""

    if isinstance(payload, dict):
        return payload.get(key)
    return getattr(payload, key, None)
