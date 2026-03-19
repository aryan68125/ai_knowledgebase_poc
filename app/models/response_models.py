"""Shared response and answer models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseResponse(BaseModel):
    """Standardized API response envelope."""

    model_config = ConfigDict(extra="forbid")

    status: int
    message: str
    data: dict[str, Any]


class QueryAnswer(BaseModel):
    """Typed answer payload used before envelope conversion."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    detailed_explanation: str
    model_thinking: str | None = None
    sources: list[str]
