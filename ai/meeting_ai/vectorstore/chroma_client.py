"""One shared persistent ChromaDB client per folder (used by AI layer and backend)."""
from __future__ import annotations

import threading
from pathlib import Path

import chromadb
from chromadb.config import Settings

_clients: dict[str, object] = {}
_lock = threading.Lock()


def get_chroma_client(path: str):
    resolved = str(Path(path).expanduser().resolve())
    with _lock:
        if resolved not in _clients:
            Path(resolved).mkdir(parents=True, exist_ok=True)
            _clients[resolved] = chromadb.PersistentClient(
                path=resolved, settings=Settings(anonymized_telemetry=False)
            )
        return _clients[resolved]
