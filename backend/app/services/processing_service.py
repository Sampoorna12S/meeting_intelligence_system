"""Stage 1: transcript indexing. Chat only depends on this finishing."""
from __future__ import annotations

import logging

from meeting_ai.ingestion.chunker import chunk_turns
from meeting_ai.ingestion.parser import Turn, parse_transcript

from ..container import Container
from . import intelligence_extractor

logger = logging.getLogger(__name__)


def validate_and_parse(content: bytes) -> list[Turn]:
    """Cheap synchronous check done in the upload request so bad files get a clear 400."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The file must be UTF-8 encoded text.") from exc
    if not text.strip():
        raise ValueError("The file is empty.")
    return parse_transcript(text)  # raises TranscriptParseError (a ValueError)


def run_indexing(container: Container, session_id: str, turns: list[Turn]) -> None:
    """Runs as a FastAPI background task: chunk -> embed -> store -> mark completed -> start extraction."""
    store = container.session_store
    try:
        if not store.set_indexing(session_id, "processing", stage="chunking"):
            return
        chunks = chunk_turns(turns)

        store.set_indexing(session_id, "processing", stage="embedding")
        embeddings = container.chunk_store.embed(chunks)

        store.set_indexing(session_id, "processing", stage="storing")
        container.chunk_store.add_chunks(session_id, chunks, embeddings=embeddings)

        if store.is_deleted(session_id):  # session was deleted while we were working
            container.chunk_store.delete_session(session_id)
            return
        store.set_chunk_count(session_id, len(chunks))
        store.set_indexing(session_id, "completed")
    except Exception as exc:
        logger.exception("Indexing failed for %s", session_id)
        try:
            container.chunk_store.delete_session(session_id)
        except Exception:
            pass
        store.set_indexing(session_id, "failed", error=f"Indexing failed: {str(exc)[:300]}")
        return

    # Chat is already enabled at this point. Extraction runs on its own and never blocks it.
    intelligence_extractor.start_all(container, session_id)
