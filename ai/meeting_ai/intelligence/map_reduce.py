"""Windowing helpers so long transcripts fit into the LLM context."""
from __future__ import annotations

import json
from typing import Callable, TypeVar

from pydantic import BaseModel

from ..llm.client import ChatModel
from ..llm.json_utils import ask_json

M = TypeVar("M", bound=BaseModel)


def split_windows(text: str, max_chars: int) -> list[str]:
    """Split on line boundaries into windows of at most ``max_chars`` (single long lines are cut)."""
    if len(text) <= max_chars:
        return [text]
    windows: list[str] = []
    current: list[str] = []
    size = 0
    for line in text.split("\n"):
        while len(line) > max_chars:
            if current:
                windows.append("\n".join(current))
                current, size = [], 0
            windows.append(line[:max_chars])
            line = line[max_chars:]
        if current and size + len(line) + 1 > max_chars:
            windows.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + 1
    if current:
        windows.append("\n".join(current))
    return windows


def _dedupe(items: list[dict], key: str) -> list[dict]:
    seen: set[str] = set()
    out = []
    for item in items:
        k = " ".join(str(item.get(key, "")).lower().split())
        if k and k not in seen:
            seen.add(k)
            out.append(item)
    return out


def extract_list(
    llm: ChatModel,
    transcript: str,
    max_chars: int,
    *,
    key: str,
    text_field: str,
    result_model: type[M],
    extract_prompt: Callable[[str], list[dict]],
    merge_prompt: Callable[[str], list[dict]],
) -> list:
    """Extract a list (decisions / action items), windowing long transcripts and merging the parts."""

    def validate(data) -> M:
        if isinstance(data, list):
            data = {key: data}
        return result_model.model_validate(data)

    windows = split_windows(transcript, max_chars)
    items: list[dict] = []
    for window in windows:
        result = ask_json(llm, extract_prompt(window), validate)
        items.extend(i.model_dump() for i in getattr(result, key))

    if len(windows) > 1 and items:
        payload = json.dumps({key: items}, ensure_ascii=False)
        if len(payload) <= max_chars:
            merged = ask_json(llm, merge_prompt(payload), validate)
            items = [i.model_dump() for i in getattr(merged, key)]
        else:
            items = _dedupe(items, text_field)
    return list(getattr(result_model.model_validate({key: items}), key))
