"""HTTP API for query requests."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.logger import ATHENA_LOGGER
from app.services.query_service import QueryService

router: APIRouter = APIRouter()
_query_service: QueryService = QueryService()


@router.get("/query")
def query_endpoint(query: str) -> object:
    """Handle query requests using service orchestration."""

    try:
        ATHENA_LOGGER.info(
            module="app.api.query_api",
            class_name="QueryAPI",
            method="query_endpoint",
            message="Query API request received",
            extra={"query": query},
        )
        response = _query_service.answer_user_query(query=query)
        ATHENA_LOGGER.info(
            module="app.api.query_api",
            class_name="QueryAPI",
            method="query_endpoint",
            message="Query API request completed",
            status_code=response.status,
            extra={"query": query},
        )
        return response
    except Exception as exc:
        ATHENA_LOGGER.error(
            module="app.api.query_api",
            class_name="QueryAPI",
            method="query_endpoint",
            message="Query API request failed",
            extra={"query": query, "error": str(exc)},
        )
        raise Exception(f"[query_endpoint] {str(exc)}") from exc
