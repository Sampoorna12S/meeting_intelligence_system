from __future__ import annotations

from ..llm.client import ChatModel
from ..llm.json_utils import StructuredOutputError
from ..prompts import summary as prompts
from .map_reduce import split_windows

_MAX_ROUNDS = 5


def generate_summary(llm: ChatModel, transcript: str, max_chars: int) -> str:
    windows = split_windows(transcript, max_chars)
    if len(windows) == 1:
        summary = llm.complete(prompts.single(transcript), temperature=0.2)
    else:
        parts = [
            llm.complete(prompts.part(w, i + 1, len(windows)), temperature=0.2)
            for i, w in enumerate(windows)
        ]
        summary = ""
        for _ in range(_MAX_ROUNDS):
            combined = "\n\n".join(parts)
            if len(combined) <= max_chars:
                summary = llm.complete(prompts.merge(combined), temperature=0.2)
                break
            parts = [llm.complete(prompts.merge(g), temperature=0.2) for g in split_windows(combined, max_chars)]
        else:
            summary = "\n\n".join(parts)[:max_chars]
    summary = summary.strip()
    if not summary:
        raise StructuredOutputError("The LLM returned an empty summary.")
    return summary
