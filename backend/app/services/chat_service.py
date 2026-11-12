"""Chat depends only on indexing status, never on intelligence extraction."""
from __future__ import annotations

from meeting_ai.rag.pipeline import Answer

from ..container import Container

HISTORY_LIMIT = 6


class SessionNotFound(Exception):
    pass


class IndexingNotReady(Exception):
    pass


def answer_question(container: Container, session_id: str, question: str, history: list[dict]) -> Answer:
    indexing = container.session_store.get_indexing(session_id)
    if indexing is None:
        raise SessionNotFound(session_id)
    if indexing["status"] != "completed":
        raise IndexingNotReady(indexing["status"])
    return container.rag.answer(session_id, question, history[-HISTORY_LIMIT:])
