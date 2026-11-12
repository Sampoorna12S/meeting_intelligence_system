"""Settings for the AI layer.

The backend builds an ``AIConfig`` from its own settings; the CLI builds one from
environment variables / a local ``.env`` file via ``AIConfig.from_env``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AIConfig:
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_path: str = "./data/chroma"
    retrieval_top_k: int = 5
    # Above this many characters the transcript is processed in windows (map-reduce).
    extraction_max_chars: int = 24000

    @classmethod
    def from_env(cls) -> "AIConfig":
        from dotenv import load_dotenv

        load_dotenv()
        env = os.environ
        return cls(
            llm_base_url=env.get("LLM_BASE_URL", ""),
            llm_api_key=env.get("LLM_API_KEY", ""),
            llm_model=env.get("LLM_MODEL", ""),
            embedding_model=env.get("EMBEDDING_MODEL", cls.embedding_model),
            chroma_path=env.get("CHROMA_PATH", cls.chroma_path),
            retrieval_top_k=int(env.get("RETRIEVAL_TOP_K", cls.retrieval_top_k)),
            extraction_max_chars=int(env.get("EXTRACTION_MAX_CHARS", cls.extraction_max_chars)),
        )
