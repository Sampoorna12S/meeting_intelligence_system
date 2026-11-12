from __future__ import annotations

from pathlib import Path

from meeting_ai.config import AIConfig
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_path: str = "./data/chroma"
    max_upload_mb: float = 2
    retrieval_top_k: int = 5
    extraction_concurrency: int = 2
    extraction_max_chars: int = 24000
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def chroma_abs_path(self) -> str:
        path = Path(self.chroma_path)
        return str(path if path.is_absolute() else (BACKEND_DIR / path).resolve())

    def ai_config(self) -> AIConfig:
        return AIConfig(
            llm_base_url=self.llm_base_url,
            llm_api_key=self.llm_api_key,
            llm_model=self.llm_model,
            embedding_model=self.embedding_model,
            chroma_path=self.chroma_abs_path,
            retrieval_top_k=self.retrieval_top_k,
            extraction_max_chars=self.extraction_max_chars,
        )


settings = Settings()
