"""Connector implementations for supported ingestion sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

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


class TeamsConnector(BaseConnector):
    """Microsoft Teams connector deterministic seed data."""

    source_type = SourceType.TEAMS

    def fetch_documents(self, mode: ConnectorMode) -> ConnectorFetchResult:
        """Fetch Teams documents using deterministic sample payloads."""

        try:
            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="fetch_documents",
                message="Teams fetch started",
                extra={"mode": mode.value},
            )

            documents = [
                IngestionDocument(
                    metadata=IngestionMetadata(
                        source_type=self.source_type,
                        document_id="teams-msg-001",
                        timestamp=datetime.now(timezone.utc),
                        author="platform-bot",
                        project_key="KB",
                        confidentiality="internal",
                        source_name="Teams #platform-announcements",
                        title="Onboarding Reminder",
                    ),
                    text=(
                        "New joiner onboarding this week includes access setup, "
                        "runbook walkthroughs, and service ownership contacts."
                    ),
                )
            ]

            ATHENA_LOGGER.info(
                module="app.ingestion.connectors",
                class_name="TeamsConnector",
                method="fetch_documents",
                message="Teams fetch completed",
                extra={"documents_fetched": len(documents), "mode": mode.value},
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
