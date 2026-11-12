from __future__ import annotations

from ..llm.client import ChatModel
from ..prompts import action_items as prompts
from .map_reduce import extract_list
from .models import ActionItem, ActionItemsResult


def generate_action_items(llm: ChatModel, transcript: str, max_chars: int) -> list[ActionItem]:
    return extract_list(
        llm,
        transcript,
        max_chars,
        key="action_items",
        text_field="task",
        result_model=ActionItemsResult,
        extract_prompt=prompts.extract,
        merge_prompt=prompts.merge,
    )
