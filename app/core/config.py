"""Application configuration definitions."""

from __future__ import annotations

import os
from pathlib import Path

from decouple import AutoConfig
from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    """Strongly typed application settings loaded from environment variables."""

    model_config = ConfigDict(extra="forbid")

    service_name: str = Field(default="knowledge-assistant-backend")
    api_prefix: str = Field(default="/api/v1")
    log_level: str = Field(default="INFO")
    log_dir: str = Field(default="app/logs")
    log_file_name: str = Field(default="app.log")
    auto_ingestion_enabled: bool = Field(default=False)
    auto_ingestion_interval_seconds: int = Field(default=900, ge=1)
    auto_ingestion_mode: str = Field(default="incremental")
    teams_connector_mode: str = Field(default="seed")
    teams_graph_enabled: bool = Field(default=False)
    teams_tenant_id: str = Field(default="")
    teams_client_id: str = Field(default="")
    teams_client_secret: str = Field(default="")
    teams_team_id: str = Field(default="")
    teams_channel_id: str = Field(default="")
    teams_graph_base_url: str = Field(default="https://graph.microsoft.com/v1.0")
    teams_page_size: int = Field(default=50, ge=1, le=50)
    teams_max_pages: int = Field(default=20, ge=1, le=200)
    teams_incremental_lookback_seconds: int = Field(default=3600, ge=1)
    teams_request_timeout_seconds: int = Field(default=30, ge=1, le=120)
    teams_source_name: str = Field(default="Teams")
    teams_project_key: str = Field(default="KB")
    teams_confidentiality: str = Field(default="internal")
    static_chat_data_dir: str = Field(default="app/data/chat_data")
    static_documents_dir: str = Field(default="app/data/documents")
    static_project_key: str = Field(default="KB")
    static_confidentiality: str = Field(default="internal")
    hf_llm_enabled: bool = Field(default=True)
    hf_api_token: str = Field(default="")
    hf_model_id: str = Field(default="deepseek-ai/DeepSeek-R1")
    hf_chat_completion_url: str = Field(
        default="https://router.huggingface.co/v1/chat/completions"
    )
    hf_timeout_seconds: int = Field(default=60, ge=1, le=180)
    hf_max_tokens: int = Field(default=700, ge=64, le=4096)
    hf_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    vector_db_provider: str = Field(default="qdrant_local")
    vector_db_path: str = Field(default="app/vector_db/qdrant")
    vector_db_collection_name: str = Field(default="knowledgebase_chunks")
    vector_db_dimension: int = Field(default=384, ge=16, le=4096)
    vector_db_top_k: int = Field(default=8, ge=1, le=50)

    @classmethod
    def from_env(cls, search_path: Path | str | None = None) -> "Settings":
        """Load runtime settings from environment variables and .env files."""

        config_search_path = search_path or Path(__file__).resolve().parents[2]
        decouple_config = AutoConfig(search_path=str(config_search_path))

        return cls(
            service_name=decouple_config(
                "SERVICE_NAME",
                default=os.getenv("SERVICE_NAME", "knowledge-assistant-backend"),
                cast=str,
            ),
            api_prefix=decouple_config(
                "API_PREFIX",
                default=os.getenv("API_PREFIX", "/api/v1"),
                cast=str,
            ),
            log_level=decouple_config(
                "LOG_LEVEL",
                default=os.getenv("LOG_LEVEL", "INFO"),
                cast=str,
            ),
            log_dir=decouple_config(
                "LOG_DIR",
                default=os.getenv("LOG_DIR", "app/logs"),
                cast=str,
            ),
            log_file_name=decouple_config(
                "LOG_FILE_NAME",
                default=os.getenv("LOG_FILE_NAME", "app.log"),
                cast=str,
            ),
            auto_ingestion_enabled=decouple_config(
                "AUTO_INGESTION_ENABLED",
                default=os.getenv("AUTO_INGESTION_ENABLED", "false"),
                cast=bool,
            ),
            auto_ingestion_interval_seconds=decouple_config(
                "AUTO_INGESTION_INTERVAL_SECONDS",
                default=os.getenv("AUTO_INGESTION_INTERVAL_SECONDS", "900"),
                cast=int,
            ),
            auto_ingestion_mode=decouple_config(
                "AUTO_INGESTION_MODE",
                default=os.getenv("AUTO_INGESTION_MODE", "incremental"),
                cast=str,
            ).lower(),
            teams_connector_mode=decouple_config(
                "TEAMS_CONNECTOR_MODE",
                default=os.getenv("TEAMS_CONNECTOR_MODE", "seed"),
                cast=str,
            ).lower(),
            teams_graph_enabled=decouple_config(
                "TEAMS_GRAPH_ENABLED",
                default=os.getenv("TEAMS_GRAPH_ENABLED", "false"),
                cast=bool,
            ),
            teams_tenant_id=decouple_config(
                "TEAMS_TENANT_ID",
                default=os.getenv("TEAMS_TENANT_ID", ""),
                cast=str,
            ),
            teams_client_id=decouple_config(
                "TEAMS_CLIENT_ID",
                default=os.getenv("TEAMS_CLIENT_ID", ""),
                cast=str,
            ),
            teams_client_secret=decouple_config(
                "TEAMS_CLIENT_SECRET",
                default=os.getenv("TEAMS_CLIENT_SECRET", ""),
                cast=str,
            ),
            teams_team_id=decouple_config(
                "TEAMS_TEAM_ID",
                default=os.getenv("TEAMS_TEAM_ID", ""),
                cast=str,
            ),
            teams_channel_id=decouple_config(
                "TEAMS_CHANNEL_ID",
                default=os.getenv("TEAMS_CHANNEL_ID", ""),
                cast=str,
            ),
            teams_graph_base_url=decouple_config(
                "TEAMS_GRAPH_BASE_URL",
                default=os.getenv("TEAMS_GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0"),
                cast=str,
            ),
            teams_page_size=decouple_config(
                "TEAMS_PAGE_SIZE",
                default=os.getenv("TEAMS_PAGE_SIZE", "50"),
                cast=int,
            ),
            teams_max_pages=decouple_config(
                "TEAMS_MAX_PAGES",
                default=os.getenv("TEAMS_MAX_PAGES", "20"),
                cast=int,
            ),
            teams_incremental_lookback_seconds=decouple_config(
                "TEAMS_INCREMENTAL_LOOKBACK_SECONDS",
                default=os.getenv("TEAMS_INCREMENTAL_LOOKBACK_SECONDS", "3600"),
                cast=int,
            ),
            teams_request_timeout_seconds=decouple_config(
                "TEAMS_REQUEST_TIMEOUT_SECONDS",
                default=os.getenv("TEAMS_REQUEST_TIMEOUT_SECONDS", "30"),
                cast=int,
            ),
            teams_source_name=decouple_config(
                "TEAMS_SOURCE_NAME",
                default=os.getenv("TEAMS_SOURCE_NAME", "Teams"),
                cast=str,
            ),
            teams_project_key=decouple_config(
                "TEAMS_PROJECT_KEY",
                default=os.getenv("TEAMS_PROJECT_KEY", "KB"),
                cast=str,
            ),
            teams_confidentiality=decouple_config(
                "TEAMS_CONFIDENTIALITY",
                default=os.getenv("TEAMS_CONFIDENTIALITY", "internal"),
                cast=str,
            ),
            static_chat_data_dir=decouple_config(
                "STATIC_CHAT_DATA_DIR",
                default=os.getenv("STATIC_CHAT_DATA_DIR", "app/data/chat_data"),
                cast=str,
            ),
            static_documents_dir=decouple_config(
                "STATIC_DOCUMENTS_DIR",
                default=os.getenv("STATIC_DOCUMENTS_DIR", "app/data/documents"),
                cast=str,
            ),
            static_project_key=decouple_config(
                "STATIC_PROJECT_KEY",
                default=os.getenv("STATIC_PROJECT_KEY", "KB"),
                cast=str,
            ),
            static_confidentiality=decouple_config(
                "STATIC_CONFIDENTIALITY",
                default=os.getenv("STATIC_CONFIDENTIALITY", "internal"),
                cast=str,
            ),
            hf_llm_enabled=decouple_config(
                "HF_LLM_ENABLED",
                default=os.getenv("HF_LLM_ENABLED", "true"),
                cast=bool,
            ),
            hf_api_token=decouple_config(
                "HF_API_TOKEN",
                default=os.getenv("HF_API_TOKEN", ""),
                cast=str,
            ),
            hf_model_id=decouple_config(
                "HF_MODEL_ID",
                default=os.getenv("HF_MODEL_ID", "deepseek-ai/DeepSeek-R1"),
                cast=str,
            ),
            hf_chat_completion_url=decouple_config(
                "HF_CHAT_COMPLETION_URL",
                default=os.getenv(
                    "HF_CHAT_COMPLETION_URL",
                    "https://router.huggingface.co/v1/chat/completions",
                ),
                cast=str,
            ),
            hf_timeout_seconds=decouple_config(
                "HF_TIMEOUT_SECONDS",
                default=os.getenv("HF_TIMEOUT_SECONDS", "60"),
                cast=int,
            ),
            hf_max_tokens=decouple_config(
                "HF_MAX_TOKENS",
                default=os.getenv("HF_MAX_TOKENS", "700"),
                cast=int,
            ),
            hf_temperature=decouple_config(
                "HF_TEMPERATURE",
                default=os.getenv("HF_TEMPERATURE", "0.2"),
                cast=float,
            ),
            vector_db_provider=decouple_config(
                "VECTOR_DB_PROVIDER",
                default=os.getenv("VECTOR_DB_PROVIDER", "qdrant_local"),
                cast=str,
            ).lower(),
            vector_db_path=decouple_config(
                "VECTOR_DB_PATH",
                default=os.getenv("VECTOR_DB_PATH", "app/vector_db/qdrant"),
                cast=str,
            ),
            vector_db_collection_name=decouple_config(
                "VECTOR_DB_COLLECTION_NAME",
                default=os.getenv("VECTOR_DB_COLLECTION_NAME", "knowledgebase_chunks"),
                cast=str,
            ),
            vector_db_dimension=decouple_config(
                "VECTOR_DB_DIMENSION",
                default=os.getenv("VECTOR_DB_DIMENSION", "384"),
                cast=int,
            ),
            vector_db_top_k=decouple_config(
                "VECTOR_DB_TOP_K",
                default=os.getenv("VECTOR_DB_TOP_K", "8"),
                cast=int,
            ),
        )


SETTINGS: Settings = Settings.from_env()
