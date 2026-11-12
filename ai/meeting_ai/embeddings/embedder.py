"""Local sentence-transformers embeddings (model is loaded lazily)."""
from __future__ import annotations

import threading
from typing import Protocol


class EmbedderProtocol(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class Embedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            return self._model

    def warm_up(self) -> None:
        """Load the model now (the first load downloads it, which can take a while)."""
        self._load()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._load().encode(
            texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
