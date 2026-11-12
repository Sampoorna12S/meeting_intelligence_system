"""Prompts for extracting action items."""
from __future__ import annotations

EXTRACT = """TASK: ACTION_ITEMS
Extract the action items from this meeting transcript: concrete tasks someone committed to or was asked to do.

Reply with ONLY a JSON object in exactly this shape:
{"action_items": [{"task": "<what needs to be done>", "owner": "<the responsible speaker, or null if unclear>", "due": "<deadline exactly as mentioned, or null>", "timestamp": "<HH:MM:SS from the transcript, or null>"}]}
Use an empty list if there are none. Never guess an owner or a deadline that is not stated. Use only the transcript."""

MERGE = """TASK: ACTION_ITEMS_MERGE
Below are action items extracted from different parts of the same meeting. Merge them into one list: remove duplicates and near-duplicates, keep meeting order.

Reply with ONLY a JSON object in exactly this shape:
{"action_items": [{"task": "<text>", "owner": "<name or null>", "due": "<deadline or null>", "timestamp": "<HH:MM:SS or null>"}]}"""


def extract(transcript: str) -> list[dict]:
    return [{"role": "system", "content": EXTRACT}, {"role": "user", "content": transcript}]


def merge(items_json: str) -> list[dict]:
    return [{"role": "system", "content": MERGE}, {"role": "user", "content": items_json}]
