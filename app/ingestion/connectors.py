"""Connector implementations for supported ingestion sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from html import unescape
import json
from pathlib import Path
import re
from typing import Any, Callable, Protocol
from urllib import parse, request
import xml.etree.ElementTree as ET
import zipfile

from app.core.config import SETTINGS, Settings
from app.core.logger import ATHENA_LOGGER
from app.models.enums import ConnectorMode, SourceType
from app.models.ingestion_models import ConnectorFetchResult, IngestionDocument, IngestionMetadata


class BaseConnector(ABC):
    """Base connector interface for ingestion sources."""

    source_type: SourceType

    @abstractmethod
    def fetch_documents(self, mode: ConnectorMode) -> ConnectorFetchResult:
        """Fetch source documents for ingestion."""

        raise NotImplementedError


class _GraphTransportProtocol(Protocol):
    """Contract for Graph API HTTP transport used by Teams connector."""

    def post_form(self, url: str, data: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
        """POST urlencoded form payload and parse JSON response."""

    def get_json(self, url: str, headers: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
        """GET JSON payload from API endpoint."""


class _UrllibGraphTransport:
    """Graph API transport backed by Python urllib."""

    def post_form(self, url: str, data: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
        """POST form-encoded data and return decoded JSON payload."""

        try:
            ATHENA_LOGGER.debug(
                module="app.ingestion.connectors",
                class_name="_UrllibGraphTransport",
                method="post_form",
                message="Graph transport POST started",
                extra={"url": url, "timeout_seconds": timeout_seconds},
            )
            encoded_data = parse.urlencode(data).encode("utf-8")
            http_request = request.Request(
                url=url,
                data=encoded_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            ATHENA_LOGGER.debug(
                module="app.ingestion.connectors",
                class_name="_UrllibGraphTransport",
                method="post_form",
                message="Graph transport POST completed",
                extra={"url": url},
            )
            return payload
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="_UrllibGraphTransport",
                method="post_form",
                message="Graph transport POST failed",
                extra={"url": url, "error": str(exc)},
            )
            raise Exception(f"[_UrllibGraphTransport.post_form] {str(exc)}") from exc

    def get_json(self, url: str, headers: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
        """GET JSON response body from Graph endpoint."""

        try:
            ATHENA_LOGGER.debug(
                module="app.ingestion.connectors",
                class_name="_UrllibGraphTransport",
                method="get_json",
                message="Graph transport GET started",
                extra={"url": url, "timeout_seconds": timeout_seconds},
            )
            http_request = request.Request(
                url=url,
                headers=headers,
                method="GET",
            )
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            ATHENA_LOGGER.debug(
                module="app.ingestion.connectors",
                class_name="_UrllibGraphTransport",
                method="get_json",
                message="Graph transport GET completed",
                extra={"url": url},
            )
            return payload
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="_UrllibGraphTransport",
                method="get_json",
                message="Graph transport GET failed",
                extra={"url": url, "error": str(exc)},
            )
            raise Exception(f"[_UrllibGraphTransport.get_json] {str(exc)}") from exc


# NOTE:
# Third-party integrations are intentionally paused for now per product direction.
# This local connector is the active ingestion path so the app can serve deterministic
# knowledge from repository-managed static files across configured directories.
class LocalDirectoryConnector(BaseConnector):
    """Ingest local .json and .docx files from configured data directories."""

    source_type = SourceType.SHAREPOINT

    def __init__(
        self,
        settings: Settings | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._settings = settings or SETTINGS
        self._now_provider = now_provider or _utc_now

    def fetch_documents(self, mode: ConnectorMode) -> ConnectorFetchResult:
        """Load and normalize files from all configured local directories."""

        try:
            base_directory = Path(self._settings.data_base_dir)
            
            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="LocalDirectoryConnector",
                method="fetch_documents",
                message="Local directory ingestion started",
                extra={
                    "mode": mode.value, 
                    "base_directory": str(base_directory),
                    "scan_directories": self._settings.data_scan_directories
                },
            )

            if not base_directory.exists():
                ATHENA_LOGGER.warning(
                    module="app.ingestion.connectors",
                    class_name="LocalDirectoryConnector",
                    method="fetch_documents",
                    message="Local base directory does not exist",
                    extra={"base_directory": str(base_directory)},
                )
                return ConnectorFetchResult(documents=[])

            documents: list[IngestionDocument] = []
            
            for sub_dir in self._settings.data_scan_directories:
                clean_sub_dir = sub_dir.strip().strip("/")
                target_dir = base_directory / clean_sub_dir
                
                if not target_dir.exists():
                    ATHENA_LOGGER.warning(
                        module="app.ingestion.connectors",
                        class_name="LocalDirectoryConnector",
                        method="fetch_documents",
                        message="Configured scan directory does not exist",
                        extra={"target_dir": str(target_dir)},
                    )
                    continue
                    
                for file_path in sorted(target_dir.iterdir()):
                    if not file_path.is_file():
                        continue
                        
                    ext = file_path.suffix.lower()
                    if ext == ".json":
                        documents.extend(self._documents_from_chat_file(file_path=file_path))
                    elif ext == ".docx":
                        doc = self._document_from_docx_file(file_path=file_path)
                        if doc:
                            documents.append(doc)

            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="LocalDirectoryConnector",
                method="fetch_documents",
                message="Local directory ingestion completed",
                extra={"documents_fetched": len(documents), "mode": mode.value},
            )
            return ConnectorFetchResult(documents=documents)
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="LocalDirectoryConnector",
                method="fetch_documents",
                message="Local directory ingestion failed",
                extra={"error": str(exc), "mode": mode.value},
            )
            raise Exception(f"[LocalDirectoryConnector.fetch_documents] {str(exc)}") from exc

    def _documents_from_chat_file(self, file_path: Path) -> list[IngestionDocument]:
        """Convert one chat JSON export file into normalized ingestion documents."""

        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            raw_messages = payload.get("value", [])
            if not isinstance(raw_messages, list):
                return []

            documents: list[IngestionDocument] = []
            for index, raw_message in enumerate(raw_messages, start=1):
                if not isinstance(raw_message, dict):
                    continue

                message_id = str(raw_message.get("id", "")).strip() or f"{file_path.stem}-{index}"
                timestamp = _parse_iso_datetime(
                    raw_timestamp=str(
                        raw_message.get("createdDateTime")
                        or raw_message.get("lastModifiedDateTime")
                        or ""
                    ).strip(),
                    fallback=self._now_provider(),
                )
                author = _extract_author(raw_message)
                subject = str(raw_message.get("subject", "")).strip()
                text = _extract_chat_message_text(raw_message)
                if not text:
                    continue

                documents.append(
                    IngestionDocument(
                        metadata=IngestionMetadata(
                            source_type=SourceType.TEAMS,
                            document_id=message_id,
                            timestamp=timestamp,
                            author=author,
                            project_key=self._settings.static_project_key,
                            confidentiality=self._settings.static_confidentiality,
                            source_name=f"Local Data / {file_path.parent.name}/{file_path.name}",
                            title=subject or f"Chat message {message_id}",
                        ),
                        text=text,
                    )
                )

            ATHENA_LOGGER.debug(
                module="app.ingestion.connectors",
                class_name="LocalDirectoryConnector",
                method="_documents_from_chat_file",
                message="Local chat file normalized",
                extra={"file_path": str(file_path), "documents_fetched": len(documents)},
            )
            return documents
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="LocalDirectoryConnector",
                method="_documents_from_chat_file",
                message="Failed to normalize local chat file",
                extra={"file_path": str(file_path), "error": str(exc)},
            )
            raise Exception(f"[LocalDirectoryConnector._documents_from_chat_file] {str(exc)}") from exc

    def _document_from_docx_file(self, file_path: Path) -> IngestionDocument | None:
        """Extract text content from .docx and return an ingestion document."""

        try:
            text = self._extract_docx_text(file_path=file_path)
            if not text:
                return None
            timestamp = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            return IngestionDocument(
                metadata=IngestionMetadata(
                    source_type=SourceType.SHAREPOINT,
                    document_id=file_path.stem,
                    timestamp=timestamp,
                    author="local-documents-loader",
                    project_key=self._settings.static_project_key,
                    confidentiality=self._settings.static_confidentiality,
                    source_name=f"Local Data / {file_path.parent.name}/{file_path.name}",
                    title=file_path.stem,
                ),
                text=text,
            )
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="LocalDirectoryConnector",
                method="_document_from_docx_file",
                message="Failed to normalize local document file",
                extra={"file_path": str(file_path), "error": str(exc)},
            )
            raise Exception(f"[LocalDirectoryConnector._document_from_docx_file] {str(exc)}") from exc

    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text content from .docx by reading word/document.xml."""

        try:
            with zipfile.ZipFile(file_path) as archive:
                document_xml = archive.read("word/document.xml")
            root = ET.fromstring(document_xml)
            namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            text_nodes = root.findall(".//w:t", namespace)
            extracted_text = _normalize_whitespace(
                " ".join(node.text for node in text_nodes if node.text)
            )
            ATHENA_LOGGER.debug(
                module="app.ingestion.connectors",
                class_name="LocalDirectoryConnector",
                method="_extract_docx_text",
                message="Extracted text from local document",
                extra={"file_path": str(file_path), "text_length": len(extracted_text)},
            )
            return extracted_text
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="LocalDirectoryConnector",
                method="_extract_docx_text",
                message="Failed to extract text from local document",
                extra={"file_path": str(file_path), "error": str(exc)},
            )
            raise Exception(f"[LocalDirectoryConnector._extract_docx_text] {str(exc)}") from exc


# NOTE:
# Graph-based integration connector is kept in repository intentionally.
# It is not the active default ingestion source right now, but we retain it so
# future integration work can be resumed without reconstructing the implementation.
class TeamsConnector(BaseConnector):
    """Microsoft Teams connector supporting seed + Graph mixed modes."""

    source_type = SourceType.TEAMS
    _supported_modes: set[str] = {"seed", "channel_messages", "get_all_messages"}

    def __init__(
        self,
        settings: Settings | None = None,
        transport: _GraphTransportProtocol | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._settings = settings or SETTINGS
        self._transport = transport or _UrllibGraphTransport()
        self._now_provider = now_provider or _utc_now

    def fetch_documents(self, mode: ConnectorMode) -> ConnectorFetchResult:
        """Fetch Teams documents from seed or Microsoft Graph based on connector settings."""

        try:
            connector_mode = self._resolve_connector_mode()
            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="fetch_documents",
                message="Teams fetch started",
                extra={
                    "mode": mode.value,
                    "connector_mode": connector_mode,
                    "teams_graph_enabled": self._settings.teams_graph_enabled,
                },
            )

            documents = self._seed_documents()
            if self._settings.teams_graph_enabled and connector_mode != "seed":
                access_token = self._request_access_token()
                if connector_mode == "channel_messages":
                    documents = self._fetch_channel_messages(access_token=access_token)
                elif connector_mode == "get_all_messages":
                    documents = self._fetch_all_channel_messages(
                        access_token=access_token,
                        ingestion_mode=mode,
                    )

            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="fetch_documents",
                message="Teams fetch completed",
                extra={
                    "documents_fetched": len(documents),
                    "mode": mode.value,
                    "connector_mode": connector_mode,
                },
            )
            return ConnectorFetchResult(documents=documents)
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="fetch_documents",
                message="Teams fetch failed",
                extra={"error": str(exc), "mode": mode.value},
            )
            raise Exception(f"[TeamsConnector.fetch_documents] {str(exc)}") from exc

    def _resolve_connector_mode(self) -> str:
        """Resolve and sanitize connector mode from settings."""

        requested_mode = self._settings.teams_connector_mode.strip().lower()
        if requested_mode in self._supported_modes:
            return requested_mode

        ATHENA_LOGGER.warning(
            module="app.ingestion.connectors",
            class_name="TeamsConnector",
            method="_resolve_connector_mode",
            message="Unsupported Teams connector mode; falling back to seed",
            extra={"requested_mode": requested_mode},
        )
        return "seed"

    def _request_access_token(self) -> str:
        """Acquire application token using client-credentials OAuth flow."""

        self._validate_graph_configuration()

        try:
            token_url = (
                f"https://login.microsoftonline.com/"
                f"{self._settings.teams_tenant_id}/oauth2/v2.0/token"
            )
            payload = {
                "client_id": self._settings.teams_client_id,
                "scope": "https://graph.microsoft.com/.default",
                "client_secret": self._settings.teams_client_secret,
                "grant_type": "client_credentials",
            }
            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="_request_access_token",
                message="Requesting Teams Graph access token",
                extra={"tenant_id_present": bool(self._settings.teams_tenant_id)},
            )
            token_response = self._transport.post_form(
                url=token_url,
                data=payload,
                timeout_seconds=self._settings.teams_request_timeout_seconds,
            )
            access_token = str(token_response.get("access_token", "")).strip()
            if not access_token:
                raise ValueError("access_token is missing in token response")
            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="_request_access_token",
                message="Teams Graph access token acquired",
            )
            return access_token
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="_request_access_token",
                message="Teams Graph access token request failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[TeamsConnector._request_access_token] {str(exc)}") from exc

    def _fetch_channel_messages(self, access_token: str) -> list[IngestionDocument]:
        """Fetch messages from a specific configured team channel."""

        try:
            graph_base_url = self._settings.teams_graph_base_url.rstrip("/")
            team_id = parse.quote(self._settings.teams_team_id, safe="")
            channel_id = parse.quote(self._settings.teams_channel_id, safe="")
            query = parse.urlencode({"$top": self._settings.teams_page_size})
            initial_url = (
                f"{graph_base_url}/teams/{team_id}/channels/{channel_id}/messages?{query}"
            )
            return self._fetch_documents_from_graph_pages(
                initial_url=initial_url,
                access_token=access_token,
            )
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="_fetch_channel_messages",
                message="Teams channel message fetch failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[TeamsConnector._fetch_channel_messages] {str(exc)}") from exc

    def _fetch_all_channel_messages(
        self,
        access_token: str,
        ingestion_mode: ConnectorMode,
    ) -> list[IngestionDocument]:
        """Fetch messages from all channels in the configured team."""

        try:
            graph_base_url = self._settings.teams_graph_base_url.rstrip("/")
            team_id = parse.quote(self._settings.teams_team_id, safe="")
            params: dict[str, str | int] = {"$top": self._settings.teams_page_size}

            if ingestion_mode == ConnectorMode.INCREMENTAL:
                cutoff = self._now_provider() - timedelta(
                    seconds=self._settings.teams_incremental_lookback_seconds
                )
                cutoff_text = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
                params["$filter"] = f"lastModifiedDateTime gt {cutoff_text}"

            query = parse.urlencode(params)
            initial_url = f"{graph_base_url}/teams/{team_id}/channels/getAllMessages?{query}"
            return self._fetch_documents_from_graph_pages(
                initial_url=initial_url,
                access_token=access_token,
            )
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="_fetch_all_channel_messages",
                message="Teams getAllMessages fetch failed",
                extra={"error": str(exc), "mode": ingestion_mode.value},
            )
            raise Exception(f"[TeamsConnector._fetch_all_channel_messages] {str(exc)}") from exc

    def _fetch_documents_from_graph_pages(
        self,
        initial_url: str,
        access_token: str,
    ) -> list[IngestionDocument]:
        """Traverse Graph pages and normalize payloads into ingestion documents."""

        try:
            documents: list[IngestionDocument] = []
            request_headers = {"Authorization": f"Bearer {access_token}"}
            current_url = initial_url
            pages_processed = 0

            while current_url and pages_processed < self._settings.teams_max_pages:
                payload = self._transport.get_json(
                    url=current_url,
                    headers=request_headers,
                    timeout_seconds=self._settings.teams_request_timeout_seconds,
                )
                pages_processed += 1
                values = payload.get("value", [])
                if isinstance(values, list):
                    for message_payload in values:
                        if not isinstance(message_payload, dict):
                            continue
                        normalized = self._normalize_graph_message(message_payload)
                        if normalized is not None:
                            documents.append(normalized)

                next_link = payload.get("@odata.nextLink")
                current_url = str(next_link) if isinstance(next_link, str) else ""

            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="_fetch_documents_from_graph_pages",
                message="Teams Graph page traversal completed",
                extra={
                    "pages_processed": pages_processed,
                    "documents_fetched": len(documents),
                    "max_pages": self._settings.teams_max_pages,
                },
            )
            return documents
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="_fetch_documents_from_graph_pages",
                message="Teams Graph page traversal failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[TeamsConnector._fetch_documents_from_graph_pages] {str(exc)}") from exc

    def _normalize_graph_message(self, message_payload: dict[str, Any]) -> IngestionDocument | None:
        """Normalize a Graph message payload into ingestion model shape."""

        try:
            message_id = str(message_payload.get("id", "")).strip()
            if not message_id:
                ATHENA_LOGGER.warning(
                    module="app.ingestion.connectors",
                    class_name="TeamsConnector",
                    method="_normalize_graph_message",
                    message="Skipping Teams message because id is missing",
                )
                return None

            timestamp = self._parse_graph_timestamp(
                raw_timestamp=str(
                    message_payload.get("lastModifiedDateTime")
                    or message_payload.get("createdDateTime")
                    or ""
                ).strip()
            )
            author = self._extract_author(message_payload)
            title = str(message_payload.get("subject", "")).strip() or f"Teams message {message_id}"
            text = self._extract_message_text(message_payload)
            if not text:
                text = "[empty teams message]"

            metadata = IngestionMetadata(
                source_type=self.source_type,
                document_id=message_id,
                timestamp=timestamp,
                author=author,
                project_key=self._settings.teams_project_key,
                confidentiality=self._settings.teams_confidentiality,
                source_name=self._settings.teams_source_name,
                title=title,
            )
            return IngestionDocument(metadata=metadata, text=text)
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="_normalize_graph_message",
                message="Teams message normalization failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[TeamsConnector._normalize_graph_message] {str(exc)}") from exc

    def _parse_graph_timestamp(self, raw_timestamp: str) -> datetime:
        """Parse Graph datetime strings into timezone-aware UTC datetime."""

        if not raw_timestamp:
            return self._now_provider()

        normalized = raw_timestamp.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            ATHENA_LOGGER.warning(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="_parse_graph_timestamp",
                message="Failed to parse Teams timestamp; using current time fallback",
                extra={"raw_timestamp": raw_timestamp},
            )
            return self._now_provider()

    def _validate_graph_configuration(self) -> None:
        """Validate required Teams Graph configuration for graph-enabled modes."""

        connector_mode = self._resolve_connector_mode()
        required_keys = {
            "TEAMS_TENANT_ID": self._settings.teams_tenant_id,
            "TEAMS_CLIENT_ID": self._settings.teams_client_id,
            "TEAMS_CLIENT_SECRET": self._settings.teams_client_secret,
            "TEAMS_TEAM_ID": self._settings.teams_team_id,
        }
        if connector_mode == "channel_messages":
            required_keys["TEAMS_CHANNEL_ID"] = self._settings.teams_channel_id

        missing = [name for name, value in required_keys.items() if not str(value).strip()]
        if missing:
            missing_text = ", ".join(sorted(missing))
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="_validate_graph_configuration",
                message="Teams Graph configuration validation failed",
                extra={"missing_keys": missing},
            )
            raise ValueError(f"Missing Teams Graph configuration keys: {missing_text}")

    def _seed_documents(self) -> list[IngestionDocument]:
        """Return deterministic Teams sample payloads for local-safe mode."""

        return [
            IngestionDocument(
                metadata=IngestionMetadata(
                    source_type=self.source_type,
                    document_id="teams-msg-001",
                    timestamp=self._now_provider(),
                    author="platform-bot",
                    project_key=self._settings.teams_project_key,
                    confidentiality=self._settings.teams_confidentiality,
                    source_name=self._settings.teams_source_name,
                    title="Onboarding Reminder",
                ),
                text=(
                    "New joiner onboarding this week includes access setup, "
                    "runbook walkthroughs, and service ownership contacts."
                ),
            )
        ]

    @staticmethod
    def _extract_author(message_payload: dict[str, Any]) -> str:
        """Extract author name from Graph chatMessage payload."""

        from_payload = message_payload.get("from", {})
        if not isinstance(from_payload, dict):
            return "unknown-author"
        user_payload = from_payload.get("user", {})
        if not isinstance(user_payload, dict):
            return "unknown-author"
        author = str(user_payload.get("displayName", "")).strip()
        return author or "unknown-author"

    @staticmethod
    def _extract_message_text(message_payload: dict[str, Any]) -> str:
        """Extract and normalize message text from Graph payload."""

        body_payload = message_payload.get("body", {})
        if not isinstance(body_payload, dict):
            return ""

        body_text = str(body_payload.get("content", "")).strip()
        if not body_text:
            return ""
        plain_text = re.sub(r"<[^>]+>", " ", unescape(body_text))
        normalized_text = re.sub(r"\s+", " ", plain_text).strip()
        return normalized_text


class SharePointConnector(BaseConnector):
    """Microsoft SharePoint connector deterministic seed data."""

    source_type = SourceType.SHAREPOINT

    def fetch_documents(self, mode: ConnectorMode) -> ConnectorFetchResult:
        """Fetch SharePoint documents using deterministic sample payloads."""

        try:
            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="SharePointConnector",
                method="fetch_documents",
                message="SharePoint fetch started",
                extra={"mode": mode.value},
            )

            documents = [
                IngestionDocument(
                    metadata=IngestionMetadata(
                        source_type=self.source_type,
                        document_id="sp-doc-001",
                        timestamp=datetime.now(timezone.utc),
                        author="platform-team",
                        project_key="KB",
                        confidentiality="internal",
                        source_name="SharePoint Engineering Runbooks",
                        title="Engineering Onboarding Runbook",
                    ),
                    text=(
                        "Engineering onboarding runbooks are in SharePoint under "
                        "Runbooks/Onboarding. Follow the setup checklist and owner map."
                    ),
                )
            ]

            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="SharePointConnector",
                method="fetch_documents",
                message="SharePoint fetch completed",
                extra={"documents_fetched": len(documents), "mode": mode.value},
            )
            return ConnectorFetchResult(documents=documents)
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="SharePointConnector",
                method="fetch_documents",
                message="SharePoint fetch failed",
                extra={"error": str(exc), "mode": mode.value},
            )
            raise Exception(f"[SharePointConnector.fetch_documents] {str(exc)}") from exc


class JiraConnector(BaseConnector):
    """Jira connector deterministic seed data."""

    source_type = SourceType.JIRA

    def fetch_documents(self, mode: ConnectorMode) -> ConnectorFetchResult:
        """Fetch Jira documents using deterministic sample payloads."""

        try:
            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="JiraConnector",
                method="fetch_documents",
                message="Jira fetch started",
                extra={"mode": mode.value},
            )

            documents = [
                IngestionDocument(
                    metadata=IngestionMetadata(
                        source_type=self.source_type,
                        document_id="jira-issue-kb-42",
                        timestamp=datetime.now(timezone.utc),
                        author="product-owner",
                        project_key="KB",
                        confidentiality="internal",
                        source_name="Jira Knowledgebase Project",
                        title="KB-42 Onboarding Knowledge Quality",
                    ),
                    text=(
                        "KB-42 tracks onboarding knowledge quality tasks, including "
                        "runbook completeness and citation quality checks."
                    ),
                )
            ]

            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="JiraConnector",
                method="fetch_documents",
                message="Jira fetch completed",
                extra={"documents_fetched": len(documents), "mode": mode.value},
            )
            return ConnectorFetchResult(documents=documents)
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.ingestion.connectors",
                class_name="JiraConnector",
                method="fetch_documents",
                message="Jira fetch failed",
                extra={"error": str(exc), "mode": mode.value},
            )
            raise Exception(f"[JiraConnector.fetch_documents] {str(exc)}") from exc


def _extract_chat_message_text(message_payload: dict[str, Any]) -> str:
    """Extract and normalize chat text content from Teams-like message payload."""

    body_payload = message_payload.get("body", {})
    if not isinstance(body_payload, dict):
        return ""
    raw_content = str(body_payload.get("content", "")).strip()
    if not raw_content:
        return ""
    return _normalize_whitespace(re.sub(r"<[^>]+>", " ", unescape(raw_content)))


def _extract_author(message_payload: dict[str, Any]) -> str:
    """Extract author display name from Teams-like payload."""

    from_payload = message_payload.get("from", {})
    if not isinstance(from_payload, dict):
        return "unknown-author"
    user_payload = from_payload.get("user", {})
    if not isinstance(user_payload, dict):
        return "unknown-author"
    author = str(user_payload.get("displayName", "")).strip()
    return author or "unknown-author"


def _parse_iso_datetime(raw_timestamp: str, fallback: datetime) -> datetime:
    """Parse ISO8601 timestamps and fallback to provided datetime on parse failures."""

    if not raw_timestamp:
        return fallback

    try:
        parsed = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return fallback


def _normalize_whitespace(text: str) -> str:
    """Normalize multi-space/newline text to compact single-space form."""

    return re.sub(r"\s+", " ", text).strip()


def _utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""

    return datetime.now(timezone.utc)
