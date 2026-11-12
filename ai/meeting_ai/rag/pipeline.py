"""Question -> retrieve -> context -> LLM -> answer with citations."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..llm.client import ChatModel
from ..prompts import rag as rag_prompt
from ..retrieval.retriever import Retriever
from ..vectorstore.chunk_store import ChunkRecord
from .citations import Citation, extract_citations, normalize_markers

NOT_FOUND_ANSWER = "I couldn't find anything about that in this transcript."


@dataclass
class Answer:
    answer: str
    citations: list[Citation] = field(default_factory=list)


def _format_excerpt(n: int, chunk: ChunkRecord) -> str:
    meta = chunk.metadata
    header = f"[{n}] Speakers: {meta.get('speakers', '')}"
    if meta.get("start_label"):
        span = meta["start_label"]
        if meta.get("end_label") and meta["end_label"] != meta["start_label"]:
            span += f" - {meta['end_label']}"
        header += f" | Time: {span}"
    return f"{header}\n{chunk.text}"


class RagPipeline:
    def __init__(self, retriever: Retriever, llm: ChatModel, history_limit: int = 6):
        self._retriever = retriever
        self._llm = llm
        self._history_limit = history_limit

    def answer(self, session_id: str, question: str, history: list[dict] | None = None) -> Answer:
        chunks = self._retriever.retrieve(session_id, question)
        if not chunks:
            return Answer(NOT_FOUND_ANSWER, [])
        excerpts = [_format_excerpt(i + 1, c) for i, c in enumerate(chunks)]
        recent = (history or [])[-self._history_limit :]
        messages = rag_prompt.build_messages(question, excerpts, recent)
        raw = self._llm.complete(messages, temperature=0.2)
        text = normalize_markers(raw.strip())
        return Answer(text, extract_citations(text, chunks))
