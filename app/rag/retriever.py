"""Retrieval layer entry point."""

from __future__ import annotations

import re
from typing import Any

from app.core.config import SETTINGS
from app.core.index_store import INDEX_STORE
from app.core.logger import ATHENA_LOGGER
from app.core.text_embedder import TEXT_EMBEDDER
from app.core.vector_store import VECTOR_STORE
from app.models.enums import SourceType
from app.models.query_models import RetrievalChunk, RetrievalRequest, RetrievalResult

_STOP_WORDS: set[str] = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "could",
    "current",
    "did",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "would",
}

_COST_QUERY_TERMS: set[str] = {
    "billing",
    "budget",
    "cloud",
    "cost",
    "dollar",
    "expense",
    "financial",
    "finance",
    "infrastructure",
    "monthly",
    "price",
    "spend",
    "usd",
}


class Retriever:
    """Vector-first hybrid retriever with deterministic lexical fallback."""

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

            is_cost_query = self._is_cost_query(query_tokens)
            vector_top_k = SETTINGS.vector_db_top_k
            if is_cost_query:
                # Cost/billing answers often include numbers and tables; request broader candidates.
                vector_top_k = max(vector_top_k, 60)

            vector_chunks = self._vector_chunks(request.query, top_k=vector_top_k)
            if is_cost_query:
                lexical_chunks = self._lexical_chunks_from_index(query_tokens=query_tokens)
                if lexical_chunks:
                    vector_chunks = self._merge_chunks(
                        primary_chunks=vector_chunks,
                        secondary_chunks=lexical_chunks,
                    )
                    ATHENA_LOGGER.info(
                        module="app.rag.retriever",
                        class_name="Retriever",
                        method="retrieve",
                        message="Merged lexical candidates for cost-intent retrieval",
                        extra={
                            "query": request.query,
                            "lexical_candidates": len(lexical_chunks),
                            "merged_candidates": len(vector_chunks),
                        },
                    )

            used_vector_candidates = bool(vector_chunks)
            if vector_chunks:
                corpus = vector_chunks
                ATHENA_LOGGER.info(
                    module="app.rag.retriever",
                    class_name="Retriever",
                    method="retrieve",
                    message="Using vector-store candidate corpus",
                    extra={"query": request.query, "candidate_chunks": len(corpus)},
                )
            else:
                corpus = self._corpus
                ATHENA_LOGGER.warning(
                    module="app.rag.retriever",
                    class_name="Retriever",
                    method="retrieve",
                    message="Vector-store candidates empty; falling back to seed corpus",
                    extra={"query": request.query, "seed_chunks": len(corpus)},
                )

            top_chunks = self._rank_chunks(
                query=request.query,
                query_tokens=query_tokens,
                corpus=corpus,
                is_cost_query=is_cost_query,
            )

            if not top_chunks and used_vector_candidates:
                expanded_top_k = max(vector_top_k * 2, 80)
                if expanded_top_k > vector_top_k:
                    expanded_chunks = self._vector_chunks(request.query, top_k=expanded_top_k)
                    if expanded_chunks:
                        ATHENA_LOGGER.warning(
                            module="app.rag.retriever",
                            class_name="Retriever",
                            method="retrieve",
                            message=(
                                "Initial vector candidates produced no matches; "
                                "retrying with expanded candidate pool"
                            ),
                            extra={
                                "query": request.query,
                                "initial_top_k": vector_top_k,
                                "expanded_top_k": expanded_top_k,
                                "expanded_candidates": len(expanded_chunks),
                            },
                        )
                        top_chunks = self._rank_chunks(
                            query=request.query,
                            query_tokens=query_tokens,
                            corpus=expanded_chunks,
                            is_cost_query=is_cost_query,
                        )

            if not top_chunks and used_vector_candidates:
                ATHENA_LOGGER.warning(
                    module="app.rag.retriever",
                    class_name="Retriever",
                    method="retrieve",
                    message=(
                        "Vector candidates had no lexical/semantic matches; "
                        "retrying against seed corpus"
                    ),
                    extra={"query": request.query, "seed_chunks": len(self._corpus)},
                )
                top_chunks = self._rank_chunks(
                    query=request.query,
                    query_tokens=query_tokens,
                    corpus=self._corpus,
                    is_cost_query=is_cost_query,
                )

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

    def _rank_chunks(
        self,
        query: str,
        query_tokens: set[str],
        corpus: list[RetrievalChunk],
        is_cost_query: bool = False,
    ) -> list[RetrievalChunk]:
        """Rank corpus chunks using hybrid scoring and return top-3 matches."""

        ATHENA_LOGGER.debug(
            module="app.rag.retriever",
            class_name="Retriever",
            method="_rank_chunks",
            message="Ranking chunk corpus started",
            extra={"query": query, "candidate_chunks": len(corpus)},
        )
        scored_chunks: list[tuple[float, RetrievalChunk]] = []
        total_chunks = len(corpus)

        for position, chunk in enumerate(corpus):
            chunk_tokens = self._tokenize(chunk.excerpt)
            semantic_score = self._semantic_score(query_tokens, chunk_tokens)
            keyword_score = self._keyword_score(query, chunk.excerpt)
            recency_score = self._recency_score(position=position, total=total_chunks)
            trust_score = self._trust_score(chunk.source_type)
            cost_signal_score = self._cost_signal_score(chunk.excerpt) if is_cost_query else 0.0
            compactness_score = self._compactness_score(chunk.excerpt) if is_cost_query else 0.0
            final_score = (
                (0.4 * semantic_score)
                + (0.3 * keyword_score)
                + (0.2 * recency_score)
                + (0.1 * trust_score)
                + (0.35 * cost_signal_score)
                + (0.2 * compactness_score)
            )

            if semantic_score > 0.0 or keyword_score > 0.0 or cost_signal_score >= 0.6:
                scored_chunks.append((final_score, chunk))

        scored_chunks.sort(key=lambda item: item[0], reverse=True)
        ranked_chunks = [item[1] for item in scored_chunks[:3]]
        ATHENA_LOGGER.debug(
            module="app.rag.retriever",
            class_name="Retriever",
            method="_rank_chunks",
            message="Ranking chunk corpus completed",
            extra={"query": query, "matched_chunks": len(ranked_chunks)},
        )
        return ranked_chunks

    def _vector_chunks(self, query: str, top_k: int) -> list[RetrievalChunk]:
        """Query configured vector store and map records to retrieval chunks."""

        try:
            query_vector = TEXT_EMBEDDER.embed(query)
            records = VECTOR_STORE.query(vector=query_vector, top_k=top_k)
            chunks: list[RetrievalChunk] = []
            for record in records:
                chunk = self._record_to_chunk(record)
                if chunk is not None:
                    chunks.append(chunk)

            ATHENA_LOGGER.debug(
                module="app.rag.retriever",
                class_name="Retriever",
                method="_vector_chunks",
                message="Vector-store retrieval candidates prepared",
                extra={"query": query, "top_k": top_k, "candidate_chunks": len(chunks)},
            )
            return chunks
        except Exception as exc:
            ATHENA_LOGGER.warning(
                module="app.rag.retriever",
                class_name="Retriever",
                method="_vector_chunks",
                message="Vector-store retrieval failed; returning empty candidates",
                extra={"query": query, "error": str(exc)},
            )
            return []

    def _lexical_chunks_from_index(self, query_tokens: set[str]) -> list[RetrievalChunk]:
        """Build lexical candidates from indexed payloads for precision-sensitive queries."""

        try:
            records = INDEX_STORE.all_records()
            scored: list[tuple[float, RetrievalChunk]] = []
            for record in records:
                chunk = self._record_to_chunk(record)
                if chunk is None:
                    continue

                excerpt_tokens = self._tokenize(chunk.excerpt)
                token_overlap = (
                    len(query_tokens.intersection(excerpt_tokens)) / len(query_tokens)
                    if query_tokens
                    else 0.0
                )
                cost_signal = self._cost_signal_score(chunk.excerpt)
                compactness = self._compactness_score(chunk.excerpt)
                has_currency_value = bool(
                    re.search(r"\$\s?\d[\d,]*(?:\.\d+)?", chunk.excerpt)
                )

                lexical_score = (
                    (0.6 * token_overlap)
                    + (0.4 * cost_signal)
                    + (0.2 * compactness)
                    + (0.2 if has_currency_value else 0.0)
                )

                if token_overlap > 0.0 or cost_signal >= 0.6:
                    scored.append((lexical_score, chunk))

            scored.sort(key=lambda item: item[0], reverse=True)
            lexical_candidates = [item[1] for item in scored[:40]]
            ATHENA_LOGGER.debug(
                module="app.rag.retriever",
                class_name="Retriever",
                method="_lexical_chunks_from_index",
                message="Lexical candidates prepared from index store",
                extra={
                    "records_scanned": len(records),
                    "lexical_candidates": len(lexical_candidates),
                },
            )
            return lexical_candidates
        except Exception as exc:
            ATHENA_LOGGER.warning(
                module="app.rag.retriever",
                class_name="Retriever",
                method="_lexical_chunks_from_index",
                message="Lexical candidate build failed",
                extra={"error": str(exc)},
            )
            return []

    def _merge_chunks(
        self,
        primary_chunks: list[RetrievalChunk],
        secondary_chunks: list[RetrievalChunk],
    ) -> list[RetrievalChunk]:
        """Merge chunk lists while preserving order and removing duplicates."""

        merged: list[RetrievalChunk] = []
        seen: set[tuple[str, str]] = set()

        for chunk in [*primary_chunks, *secondary_chunks]:
            key = (chunk.source_name, chunk.excerpt)
            if key in seen:
                continue
            seen.add(key)
            merged.append(chunk)

        return merged

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

        normalized_tokens: set[str] = set()
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower()):
            normalized = self._normalize_token(token)
            if len(normalized) <= 2:
                continue
            if normalized in _STOP_WORDS:
                continue
            normalized_tokens.add(normalized)
        return normalized_tokens

    def _record_to_chunk(self, record: dict[str, Any]) -> RetrievalChunk | None:
        """Convert indexed record payload into retrieval chunk when valid."""

        source_type_raw = str(record.get("source_type", "")).strip()
        source_name = str(record.get("source_name", "")).strip()
        text = str(record.get("text", "")).strip()
        if not source_type_raw or not source_name or not text:
            return None

        try:
            source_type = SourceType(source_type_raw)
        except Exception:
            return None

        return RetrievalChunk(
            source_type=source_type,
            source_name=source_name,
            excerpt=text,
        )

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
        excerpt_tokens = self._tokenize(excerpt)
        if not excerpt_tokens:
            return 0.0
        matched = len(query_tokens.intersection(excerpt_tokens))
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

    def _is_cost_query(self, query_tokens: set[str]) -> bool:
        """Return whether query intent is likely about cloud/financial cost topics."""

        return bool(query_tokens.intersection(_COST_QUERY_TERMS))

    def _cost_signal_score(self, excerpt: str) -> float:
        """Score excerpt for financial/cost signal strength (0..1)."""

        excerpt_tokens = self._tokenize(excerpt)
        excerpt_lower = excerpt.lower()

        term_hits = 0
        for term in _COST_QUERY_TERMS:
            if term in excerpt_tokens or term in excerpt_lower:
                term_hits += 1

        has_currency_value = bool(re.search(r"\$\s?\d[\d,]*(?:\.\d+)?", excerpt))
        score = (term_hits / 4.0) + (0.5 if has_currency_value else 0.0)
        return min(1.0, score)

    def _compactness_score(self, excerpt: str) -> float:
        """Prefer concise excerpts for direct fact-style questions."""

        word_count = len(re.findall(r"[a-zA-Z0-9]+", excerpt))
        if word_count <= 0:
            return 0.0
        # Full score for concise snippets; gently decays for long blocks.
        return min(1.0, 80.0 / float(word_count))

    def _normalize_token(self, token: str) -> str:
        """Normalize common plural forms so scoring compares like-for-like."""

        if token.endswith("ies") and len(token) > 4:
            return f"{token[:-3]}y"
        if token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
            return token[:-1]
        return token
