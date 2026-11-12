"""Transcript chunks in the ``meeting_chunks`` ChromaDB collection."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..embeddings.embedder import EmbedderProtocol
from ..ingestion.chunker import Chunk

COLLECTION = "meeting_chunks"


@dataclass
class ChunkRecord:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)
    distance: float | None = None

    @property
    def chunk_index(self) -> int:
        return int(self.metadata.get("chunk_index", 0))


class ChunkStore:
    def __init__(self, client, embedder: EmbedderProtocol):
        self._client = client
        self._embedder = embedder

    def _col(self):
        return self._client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    def embed(self, chunks: list[Chunk]) -> list[list[float]]:
        return self._embedder.embed_documents([c.text for c in chunks])

    def add_chunks(
        self,
        session_id: str,
        chunks: list[Chunk],
        embeddings: list[list[float]] | None = None,
        batch_size: int = 100,
    ) -> None:
        if not chunks:
            return
        if embeddings is None:
            embeddings = self.embed(chunks)
        col = self._col()
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            col.add(
                ids=[f"{session_id}:{c.index:04d}" for c in batch],
                documents=[c.text for c in batch],
                embeddings=embeddings[i : i + batch_size],
                metadatas=[c.metadata(session_id) for c in batch],
            )

    def query(self, session_id: str, question: str, top_k: int = 5) -> list[ChunkRecord]:
        col = self._col()
        res = col.query(
            query_embeddings=[self._embedder.embed_query(question)],
            n_results=top_k,
            where={"session_id": session_id},
            include=["documents", "metadatas", "distances"],
        )
        ids = res["ids"][0] if res["ids"] else []
        return [
            ChunkRecord(
                id=ids[i],
                text=res["documents"][0][i],
                metadata=res["metadatas"][0][i],
                distance=res["distances"][0][i],
            )
            for i in range(len(ids))
        ]

    def get_all(self, session_id: str) -> list[ChunkRecord]:
        res = self._col().get(where={"session_id": session_id}, include=["documents", "metadatas"])
        records = [
            ChunkRecord(id=res["ids"][i], text=res["documents"][i], metadata=res["metadatas"][i])
            for i in range(len(res["ids"]))
        ]
        return sorted(records, key=lambda r: r.chunk_index)

    def get_transcript_text(self, session_id: str) -> str:
        """Rebuild the transcript from stored chunks, dropping the overlap lines."""
        lines: list[str] = []
        for rec in self.get_all(session_id):
            overlap = int(rec.metadata.get("overlap_lines", 0))
            lines.extend(rec.text.split("\n")[overlap:])
        return "\n".join(lines)

    def count(self, session_id: str) -> int:
        return len(self._col().get(where={"session_id": session_id}, include=[])["ids"])

    def delete_session(self, session_id: str) -> None:
        self._col().delete(where={"session_id": session_id})
