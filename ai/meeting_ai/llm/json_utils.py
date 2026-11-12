"""Parse and validate JSON returned by the LLM, with one re-ask on failure."""
from __future__ import annotations

import json
import re
from typing import Any, Callable, TypeVar

from .client import ChatModel

T = TypeVar("T")


class StructuredOutputError(RuntimeError):
    """The LLM did not return valid output in the required format."""


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def extract_json(text: str) -> Any:
    cleaned = _FENCE.sub("", text.strip()).strip()
    try:
        return json.loads(cleaned)
    except ValueError:
        pass
    starts = [i for i in (cleaned.find("{"), cleaned.find("[")) if i != -1]
    if not starts:
        raise ValueError("no JSON found in the response")
    start = min(starts)
    end = max(cleaned.rfind("}"), cleaned.rfind("]"))
    if end <= start:
        raise ValueError("no JSON found in the response")
    return json.loads(cleaned[start : end + 1])


def ask_json(llm: ChatModel, messages: list[dict], validate: Callable[[Any], T], retries: int = 1) -> T:
    msgs = list(messages)
    last: Exception | None = None
    for _ in range(retries + 1):
        raw = llm.complete(msgs, temperature=0.1)
        try:
            return validate(extract_json(raw))
        except ValueError as exc:  # json errors and pydantic ValidationError both subclass ValueError
            last = exc
            msgs = msgs + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": "That was not valid JSON in the required format. "
                    "Reply again with ONLY the JSON, no commentary and no code fences.",
                },
            ]
    raise StructuredOutputError(f"The LLM returned invalid JSON: {last}")
