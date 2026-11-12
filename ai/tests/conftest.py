import hashlib
import math
import re

import chromadb
import pytest
from chromadb.config import Settings

from meeting_ai.vectorstore.chunk_store import ChunkStore


class FakeEmbedder:
    """Deterministic bag-of-words hashing embedder (no model download needed)."""

    dim = 128

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


@pytest.fixture
def chroma_client(tmp_path):
    return chromadb.PersistentClient(path=str(tmp_path / "chroma"), settings=Settings(anonymized_telemetry=False))


@pytest.fixture
def chunk_store(chroma_client):
    return ChunkStore(chroma_client, FakeEmbedder())


SAMPLE = """[00:00:05] Alice: Welcome everyone. Today we decide the launch date.
[00:00:20] Bob: Engineering is ready. Export might slip by a week.
[00:00:40] Alice: Launch without export then. We launch on November 21st.
[00:01:10] Carol: I will draft the customer announcement email by Friday.
[00:01:30] Dave: I will update the pricing page copy by next Wednesday.
"""
