"""Top-k retrieval for one session."""
from __future__ import annotations

from ..vectorstore.chunk_store import ChunkRecord, ChunkStore


class Retriever:
    def __init__(self, chunk_store: ChunkStore, top_k: int = 5):
        self._store = chunk_store
        self.top_k = top_k

    def retrieve(self, session_id: str, question: str) -> list[ChunkRecord]:
        records = self._store.query(session_id, question, self.top_k)
        # present excerpts in meeting order so the context reads chronologically
        return sorted(records, key=lambda r: r.chunk_index)
