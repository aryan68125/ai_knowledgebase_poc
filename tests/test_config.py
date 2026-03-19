"""Tests for environment-backed settings loading."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings


def test_settings_from_env_reads_values_from_dotenv_file(tmp_path: Path) -> None:
    """Settings loader should read values from a .env file search path."""

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "SERVICE_NAME=kb-test-service",
                "API_PREFIX=/api/test/v1",
                "LOG_LEVEL=DEBUG",
                "LOG_DIR=app/logs",
                "LOG_FILE_NAME=test.log",
                "AUTO_INGESTION_ENABLED=true",
                "AUTO_INGESTION_INTERVAL_SECONDS=900",
                "AUTO_INGESTION_MODE=incremental",
                "TEAMS_CONNECTOR_MODE=channel_messages",
                "TEAMS_GRAPH_ENABLED=true",
                "TEAMS_TENANT_ID=test-tenant-id",
                "TEAMS_CLIENT_ID=test-client-id",
                "TEAMS_CLIENT_SECRET=test-client-secret",
                "TEAMS_TEAM_ID=test-team-id",
                "TEAMS_CHANNEL_ID=test-channel-id",
                "TEAMS_GRAPH_BASE_URL=https://graph.microsoft.com/v1.0",
                "TEAMS_PAGE_SIZE=25",
                "TEAMS_MAX_PAGES=3",
                "TEAMS_INCREMENTAL_LOOKBACK_SECONDS=7200",
                "TEAMS_SOURCE_NAME=Teams Platform Channel",
                "TEAMS_PROJECT_KEY=KB",
                "TEAMS_CONFIDENTIALITY=internal",
                "STATIC_CHAT_DATA_DIR=app/data/chat_data",
                "STATIC_DOCUMENTS_DIR=app/data/documents",
                "STATIC_PROJECT_KEY=KB",
                "STATIC_CONFIDENTIALITY=internal",
                "HF_LLM_ENABLED=true",
                "HF_API_TOKEN=hf_test_token",
                "HF_MODEL_ID=deepseek-ai/DeepSeek-R1",
                "HF_CHAT_COMPLETION_URL=https://router.huggingface.co/v1/chat/completions",
                "HF_TIMEOUT_SECONDS=45",
                "HF_MAX_TOKENS=512",
                "HF_TEMPERATURE=0.2",
                "VECTOR_DB_PROVIDER=qdrant_local",
                "VECTOR_DB_PATH=app/vector_db/qdrant",
                "VECTOR_DB_COLLECTION_NAME=kb_test_vectors",
                "VECTOR_DB_DIMENSION=256",
                "VECTOR_DB_TOP_K=6",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings.from_env(search_path=tmp_path)

    assert settings.service_name == "kb-test-service"
    assert settings.api_prefix == "/api/test/v1"
    assert settings.log_level == "DEBUG"
    assert settings.log_dir == "app/logs"
    assert settings.log_file_name == "test.log"
    assert settings.auto_ingestion_enabled is True
    assert settings.auto_ingestion_interval_seconds == 900
    assert settings.auto_ingestion_mode == "incremental"
    assert settings.teams_connector_mode == "channel_messages"
    assert settings.teams_graph_enabled is True
    assert settings.teams_tenant_id == "test-tenant-id"
    assert settings.teams_client_id == "test-client-id"
    assert settings.teams_client_secret == "test-client-secret"
    assert settings.teams_team_id == "test-team-id"
    assert settings.teams_channel_id == "test-channel-id"
    assert settings.teams_graph_base_url == "https://graph.microsoft.com/v1.0"
    assert settings.teams_page_size == 25
    assert settings.teams_max_pages == 3
    assert settings.teams_incremental_lookback_seconds == 7200
    assert settings.teams_source_name == "Teams Platform Channel"
    assert settings.teams_project_key == "KB"
    assert settings.teams_confidentiality == "internal"
    assert settings.static_chat_data_dir == "app/data/chat_data"
    assert settings.static_documents_dir == "app/data/documents"
    assert settings.static_project_key == "KB"
    assert settings.static_confidentiality == "internal"
    assert settings.hf_llm_enabled is True
    assert settings.hf_api_token == "hf_test_token"
    assert settings.hf_model_id == "deepseek-ai/DeepSeek-R1"
    assert settings.hf_chat_completion_url == "https://router.huggingface.co/v1/chat/completions"
    assert settings.hf_timeout_seconds == 45
    assert settings.hf_max_tokens == 512
    assert settings.hf_temperature == 0.2
    assert settings.vector_db_provider == "qdrant_local"
    assert settings.vector_db_path == "app/vector_db/qdrant"
    assert settings.vector_db_collection_name == "kb_test_vectors"
    assert settings.vector_db_dimension == 256
    assert settings.vector_db_top_k == 6
