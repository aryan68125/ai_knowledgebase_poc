"""Tests for local directory ingestion connector."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.ingestion.connectors import LocalDirectoryConnector
from app.models.enums import ConnectorMode, SourceType


def test_local_directory_connector_loads_chat_json() -> None:
    """Connector should ingest messages from all chat_data JSON files."""

    connector = LocalDirectoryConnector(
        settings=Settings().model_copy(
            update={
                "data_base_dir": "app/data",
                "data_scan_directories": ["chat_data"],
                "static_project_key": "KB",
                "static_confidentiality": "internal",
            }
        )
    )

    result = connector.fetch_documents(mode=ConnectorMode.FULL)
    expected_file_count = len(list(Path("app/data/chat_data").glob("*.json")))

    assert expected_file_count > 0
    assert len(result.documents) >= expected_file_count
    assert all(doc.metadata.source_type == SourceType.TEAMS for doc in result.documents)
    assert all("Local Data / chat_data" in doc.metadata.source_name for doc in result.documents)


def test_local_directory_connector_loads_docx_documents() -> None:
    """Connector should ingest text from every .docx in documents folder."""

    connector = LocalDirectoryConnector(
        settings=Settings().model_copy(
            update={
                "data_base_dir": "app/data",
                "data_scan_directories": ["documents"],
                "static_project_key": "KB",
                "static_confidentiality": "internal",
            }
        )
    )

    result = connector.fetch_documents(mode=ConnectorMode.FULL)
    expected_doc_count = len(list(Path("app/data/documents").glob("*.docx")))

    assert expected_doc_count > 0
    assert len(result.documents) == expected_doc_count
    assert all(doc.metadata.source_type == SourceType.SHAREPOINT for doc in result.documents)
    assert all(len(doc.text) > 100 for doc in result.documents)
