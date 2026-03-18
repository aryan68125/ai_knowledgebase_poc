"""Retrieval layer entry point."""

from __future__ import annotations

import re

from app.core.index_store import INDEX_STORE
from app.core.logger import ATHENA_LOGGER
from app.models.enums import SourceType
from app.models.query_models import RetrievalChunk, RetrievalRequest, RetrievalResult


class Retriever:
    """Deterministic hybrid retriever with lightweight in-memory corpus."""

    def __init__(self) -> None:
        self._corpus = self._build_default_corpus()

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Retrieve relevant chunks for a user query."""

        try:
            ATHENA_LOGGER.info(
                module="app.rag.retriever",
                class_name="Retriever",
                method="retrieve",
                message="Retrieval started",
                extra={"query": request.query},
            )
            corpus = self._active_corpus()
            query_tokens = self._tokenize(request.query)
            if not query_tokens:
                ATHENA_LOGGER.warning(
                    module="app.rag.retriever",
                    class_name="Retriever",
                    method="retrieve",
                    message="Retrieval skipped due to empty token set",
                    extra={"query": request.query},
                )
                return RetrievalResult(chunks=[])

            scored_chunks: list[tuple[float, RetrievalChunk]] = []
            total_chunks = len(corpus)

            for position, chunk in enumerate(corpus):
                chunk_tokens = self._tokenize(chunk.excerpt)
                semantic_score = self._semantic_score(query_tokens, chunk_tokens)
                keyword_score = self._keyword_score(request.query, chunk.excerpt)
                recency_score = self._recency_score(position=position, total=total_chunks)
                trust_score = self._trust_score(chunk.source_type)
                final_score = (
                    (0.4 * semantic_score)
                    + (0.3 * keyword_score)
                    + (0.2 * recency_score)
                    + (0.1 * trust_score)
                )

                if semantic_score > 0.0 or keyword_score > 0.0:
                    scored_chunks.append((final_score, chunk))

            scored_chunks.sort(key=lambda item: item[0], reverse=True)
            top_chunks = [item[1] for item in scored_chunks[:3]]

            if not top_chunks:
                ATHENA_LOGGER.warning(
                    module="app.rag.retriever",
                    class_name="Retriever",
                    method="retrieve",
                    message="No chunks matched retrieval query",
                    extra={"query": request.query},
                )

            ATHENA_LOGGER.info(
                module="app.rag.retriever",
                class_name="Retriever",
                method="retrieve",
                message="Retrieval executed with hybrid ranking",
                extra={"query": request.query, "matched_chunks": len(top_chunks)},
            )
            return RetrievalResult(chunks=top_chunks)
        except Exception as exc:  # pragma: no cover - defensive boundary
            ATHENA_LOGGER.error(
                module="app.rag.retriever",
                class_name="Retriever",
                method="retrieve",
                message="Retrieval failed",
                extra={"query": request.query, "error": str(exc)},
            )
            raise Exception(f"[Retriever.retrieve] {str(exc)}") from exc

    def _active_corpus(self) -> list[RetrievalChunk]:
        """Return indexed corpus when available, otherwise fallback seed corpus."""

        try:
            indexed_chunks = self._indexed_corpus()
            if indexed_chunks:
                ATHENA_LOGGER.info(
                    module="app.rag.retriever",
                    class_name="Retriever",
                    method="_active_corpus",
                    message="Using indexed corpus for retrieval",
                    extra={"indexed_chunks": len(indexed_chunks)},
                )
                return indexed_chunks

            ATHENA_LOGGER.warning(
                module="app.rag.retriever",
                class_name="Retriever",
                method="_active_corpus",
                message="Indexed corpus empty; falling back to seed corpus",
                extra={"seed_chunks": len(self._corpus)},
            )
            return self._corpus
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.rag.retriever",
                class_name="Retriever",
                method="_active_corpus",
                message="Failed to resolve active retrieval corpus",
                extra={"error": str(exc)},
            )
            raise Exception(f"[Retriever._active_corpus] {str(exc)}") from exc

    def _indexed_corpus(self) -> list[RetrievalChunk]:
        """Build retrieval chunks from shared indexed records."""

        try:
            records = INDEX_STORE.all_records()
            chunks: list[RetrievalChunk] = []
            for record in records:
                source_type_raw = str(record.get("source_type", ""))
                text = str(record.get("text", "")).strip()
                source_name = str(record.get("source_name", "")).strip()
                if not source_type_raw or not text or not source_name:
                    continue

                try:
                    source_type = SourceType(source_type_raw)
                except Exception:
                    continue

                chunks.append(
                    RetrievalChunk(
                        source_type=source_type,
                        source_name=source_name,
                        excerpt=text,
                    )
                )

            ATHENA_LOGGER.debug(
                module="app.rag.retriever",
                class_name="Retriever",
                method="_indexed_corpus",
                message="Built indexed corpus view",
                extra={"indexed_records": len(records), "usable_chunks": len(chunks)},
            )
            return chunks
        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.rag.retriever",
                class_name="Retriever",
                method="_indexed_corpus",
                message="Failed to build indexed corpus view",
                extra={"error": str(exc)},
            )
            raise Exception(f"[Retriever._indexed_corpus] {str(exc)}") from exc

    def _build_default_corpus(self) -> list[RetrievalChunk]:
        """Build deterministic seed chunks for retrieval behavior."""

        return [
            RetrievalChunk(
                source_type=SourceType.SHAREPOINT,
                source_name="SharePoint Engineering Runbooks",
                excerpt=(
                    "Onboarding runbooks are stored in the Engineering Runbooks "
                    "library under SharePoint. Start with the New Joiner checklist."
                ),
            ),
            RetrievalChunk(
                source_type=SourceType.TEAMS,
                source_name="Teams #platform-announcements",
                excerpt=(
                    "Platform onboarding reminders are posted weekly with links to "
                    "service runbooks and environment setup steps."
                ),
            ),
            RetrievalChunk(
                source_type=SourceType.JIRA,
                source_name="JIRA KB-42",
                excerpt=(
                    "Ticket KB-42 tracks knowledgebase onboarding improvements and "
                    "documents response quality review process."
                ),
            ),
            RetrievalChunk(
                source_type=SourceType.SHAREPOINT,
                source_name="SharePoint API Guidelines",
                excerpt=(
                    "API standards include response envelopes, status handling, "
                    "and source citation expectations."
                ),
            ),
        ]

    def _tokenize(self, text: str) -> set[str]:
        """Normalize text into lowercase alphanumeric tokens."""

        return {token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(token) > 2}

    def _semantic_score(self, query_tokens: set[str], chunk_tokens: set[str]) -> float:
        """Compute semantic overlap as Jaccard similarity."""

        if not query_tokens or not chunk_tokens:
            return 0.0
        intersection_size = len(query_tokens.intersection(chunk_tokens))
        union_size = len(query_tokens.union(chunk_tokens))
        if union_size == 0:
            return 0.0
        return intersection_size / union_size

    def _keyword_score(self, query: str, excerpt: str) -> float:
        """Compute keyword score from direct token matches in excerpt."""

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return 0.0
        excerpt_lower = excerpt.lower()
        matched = sum(1 for token in query_tokens if token in excerpt_lower)
        return matched / len(query_tokens)

    def _recency_score(self, position: int, total: int) -> float:
        """Approximate recency by preferring earlier corpus entries."""

        if total <= 1:
            return 1.0
        return 1.0 - (position / (total - 1))

    def _trust_score(self, source_type: SourceType) -> float:
        """Return source trust priors used in hybrid ranking."""

        source_trust = {
            SourceType.SHAREPOINT: 0.95,
            SourceType.JIRA: 0.85,
            SourceType.TEAMS: 0.75,
        }
        return source_trust.get(source_type, 0.5)
