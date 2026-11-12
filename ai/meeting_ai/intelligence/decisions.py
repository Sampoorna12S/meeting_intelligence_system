from __future__ import annotations

from ..llm.client import ChatModel
from ..prompts import decisions as prompts
from .map_reduce import extract_list
from .models import Decision, DecisionsResult


def generate_decisions(llm: ChatModel, transcript: str, max_chars: int) -> list[Decision]:
    return extract_list(
        llm,
        transcript,
        max_chars,
        key="decisions",
        text_field="decision",
        result_model=DecisionsResult,
        extract_prompt=prompts.extract,
        merge_prompt=prompts.merge,
    )
