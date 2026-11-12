"""Thin wrapper over any OpenAI-compatible chat endpoint (Groq, Gemini, OpenAI, ...)."""
from __future__ import annotations

import threading
from typing import Protocol

from ..config import AIConfig


class LLMError(RuntimeError):
    """The LLM call failed or the LLM is not configured."""


class ChatModel(Protocol):
    def complete(self, messages: list[dict], temperature: float = 0.2) -> str: ...


class LLMClient:
    def __init__(self, config: AIConfig):
        self._config = config
        self._client = None
        self._lock = threading.Lock()

    def _get_client(self):
        with self._lock:
            if self._client is None:
                if not self._config.llm_api_key or not self._config.llm_model:
                    raise LLMError("LLM is not configured. Set LLM_API_KEY and LLM_MODEL in the .env file.")
                from openai import OpenAI

                self._client = OpenAI(
                    base_url=self._config.llm_base_url or None,
                    api_key=self._config.llm_api_key,
                    timeout=90,
                )
            return self._client

    def complete(self, messages: list[dict], temperature: float = 0.2) -> str:
        client = self._get_client()
        try:
            resp = client.chat.completions.create(
                model=self._config.llm_model, messages=messages, temperature=temperature
            )
        except LLMError:
            raise
        except Exception as exc:  # network, auth, rate limit, ...
            raise LLMError(f"LLM request failed: {exc}") from exc
        return (resp.choices[0].message.content or "").strip()
