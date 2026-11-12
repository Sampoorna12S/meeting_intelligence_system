"""Wires the AI layer, session store and scheduler together."""
from __future__ import annotations

from meeting_ai.config import AIConfig
from meeting_ai.embeddings.embedder import Embedder
from meeting_ai.llm.client import LLMClient
from meeting_ai.rag.pipeline import RagPipeline
from meeting_ai.retrieval.retriever import Retriever
from meeting_ai.vectorstore.chroma_client import get_chroma_client
from meeting_ai.vectorstore.chunk_store import ChunkStore

from .config import Settings, settings as default_settings
from .store.session_store import SessionStore
from .tasks import TaskScheduler


class Container:
    def __init__(self, settings: Settings, ai_config: AIConfig, *, embedder=None, llm=None, chroma_client=None):
        self.settings = settings
        self.ai_config = ai_config
        self.chroma_client = chroma_client or get_chroma_client(ai_config.chroma_path)
        self.embedder = embedder or Embedder(ai_config.embedding_model)
        self.llm = llm or LLMClient(ai_config)
        self.chunk_store = ChunkStore(self.chroma_client, self.embedder)
        self.retriever = Retriever(self.chunk_store, ai_config.retrieval_top_k)
        self.rag = RagPipeline(self.retriever, self.llm)
        self.session_store = SessionStore(self.chroma_client)
        self.scheduler = TaskScheduler(settings.extraction_concurrency)


def build_default_container() -> Container:
    return Container(default_settings, default_settings.ai_config())
