"""Command to split ingestion documents into structure-aware overlapping chunks."""

from __future__ import annotations

import re

import nltk

from app.commands.base_command import BaseCommand
from app.core.logger import ATHENA_LOGGER
from app.models.ingestion_models import ChunkingRequest, ChunkingResult, IndexedChunk


def _ensure_nltk_punkt() -> None:  # pragma: no cover
    """Download punkt_tab tokenizer data if not already present."""
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)


def _split_paragraphs(text: str) -> list[str]:
    """Split text on blank lines, returning non-empty paragraph strings."""
    return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]


def _build_chunks_contextually(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Build chunks up to max_tokens, prioritizing paragraph and sentence boundaries.
    
    If adding a sentence would exceed max_tokens, the current chunk is flushed.
    The next chunk begins with the last overlap_tokens words of the flushed chunk.
    If a single sentence is larger than (max_tokens - overlap_tokens), it is forcefully split by words.
    """
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return []

    chunks: list[str] = []
    current_words: list[str] = []

    for paragraph in paragraphs:
        sentences = nltk.sent_tokenize(paragraph)
        for sentence in sentences:
            sentence_words = sentence.split()
            
            while sentence_words:
                capacity = max_tokens - len(current_words)
                
                # If the entire remaining sentence fits in the current chunk
                if len(sentence_words) <= capacity:
                    current_words.extend(sentence_words)
                    break  # Done with this sentence
                
                # It doesn't fit.
                # If current chunk is substantially filled past overlap, flush it to preserve the sentence.
                if len(current_words) > overlap_tokens:
                    chunks.append(" ".join(current_words))
                    current_words = current_words[-overlap_tokens:] if overlap_tokens > 0 else []
                    continue  # Re-evaluate same sentence against fresh chunk
                
                # If we get here, the sentence is larger than (max_tokens - overlap_tokens).
                # Forcefully word-break it up to max capacity.
                take_amount = max_tokens - len(current_words)
                if take_amount <= 0:
                    chunks.append(" ".join(current_words))
                    current_words = current_words[-overlap_tokens:] if overlap_tokens > 0 else []
                    take_amount = max_tokens - len(current_words)
                    
                current_words.extend(sentence_words[:take_amount])
                sentence_words = sentence_words[take_amount:]
                
                chunks.append(" ".join(current_words))
                current_words = current_words[-overlap_tokens:] if overlap_tokens > 0 else []

    if current_words and len(current_words) > overlap_tokens:
        chunks.append(" ".join(current_words))
    elif current_words and not chunks:
        chunks.append(" ".join(current_words))

    return chunks


class ChunkDocumentCommand(BaseCommand[ChunkingRequest, ChunkingResult]):
    """Generate structure-aware overlapping chunks from a document."""

    def execute(self, input_model: ChunkingRequest) -> ChunkingResult:
        """Split a document into structure-aware chunks.

        Strategy:
        1. Split on paragraph boundaries (double newlines).
        2. For paragraphs exceeding chunk_size_tokens words, break further at
           sentence boundaries using NLTK sent_tokenize.
        3. Inject word-level overlap (chunk_overlap_tokens words) from the tail
           of chunk N into the head of chunk N+1.
        """

        try:
            _ensure_nltk_punkt()

            ATHENA_LOGGER.info(
                module="app.commands.chunk_document_command",
                class_name="ChunkDocumentCommand",
                method="execute",
                message="Structure-aware chunking started",
                extra={
                    "document_id": input_model.document.metadata.document_id,
                    "chunk_size_tokens": input_model.chunk_size_tokens,
                    "chunk_overlap_tokens": input_model.chunk_overlap_tokens,
                },
            )

            if input_model.chunk_overlap_tokens >= input_model.chunk_size_tokens:
                raise ValueError("chunk_size_tokens must be greater than chunk_overlap_tokens")

            # Step 1 & 2: Build chunks contextually aggregating paragraphs/sentences
            overlapped_chunks = _build_chunks_contextually(
                text=input_model.document.text,
                max_tokens=input_model.chunk_size_tokens,
                overlap_tokens=input_model.chunk_overlap_tokens
            )
            
            if not overlapped_chunks:
                raise ValueError("Document text produced no meaningful chunks.")

            # Step 4: build IndexedChunk objects
            chunks: list[IndexedChunk] = []
            for idx, chunk_text in enumerate(overlapped_chunks, start=1):
                words = chunk_text.split()
                if not words:
                    continue
                chunks.append(
                    IndexedChunk(
                        chunk_id=f"{input_model.document.metadata.document_id}-chunk-{idx}",
                        document_id=input_model.document.metadata.document_id,
                        source_type=input_model.document.metadata.source_type,
                        source_name=input_model.document.metadata.source_name,
                        project_key=input_model.document.metadata.project_key,
                        timestamp=input_model.document.metadata.timestamp,
                        text=chunk_text,
                        token_count=len(words),
                    )
                )

            ATHENA_LOGGER.info(
                module="app.commands.chunk_document_command",
                class_name="ChunkDocumentCommand",
                method="execute",
                message="Structure-aware chunking completed",
                extra={
                    "document_id": input_model.document.metadata.document_id,
                    "chunk_count": len(chunks),
                },
            )
            return ChunkingResult(chunks=chunks)

        except Exception as exc:
            ATHENA_LOGGER.error(
                module="app.commands.chunk_document_command",
                class_name="ChunkDocumentCommand",
                method="execute",
                message="Structure-aware chunking failed",
                extra={"error": str(exc)},
            )
            raise Exception(f"[ChunkDocumentCommand.execute] {str(exc)}") from exc
