"""Prompts for extracting key decisions."""
from __future__ import annotations

EXTRACT = """TASK: DECISIONS
Extract the key decisions that were actually made in this meeting transcript.
Only include firm decisions or agreements - not suggestions, open questions or topics still under discussion.

Reply with ONLY a JSON object in exactly this shape:
{"decisions": [{"decision": "<one clear sentence>", "speaker": "<who announced or confirmed it, or null>", "timestamp": "<HH:MM:SS from the transcript, or null>"}]}
Use an empty list if there are no decisions. Use only the transcript."""

MERGE = """TASK: DECISIONS_MERGE
Below are decisions extracted from different parts of the same meeting. Merge them into one list: remove duplicates and near-duplicates, keep the earliest timestamp, keep meeting order.

Reply with ONLY a JSON object in exactly this shape:
{"decisions": [{"decision": "<one clear sentence>", "speaker": "<name or null>", "timestamp": "<HH:MM:SS or null>"}]}"""


def extract(transcript: str) -> list[dict]:
    return [{"role": "system", "content": EXTRACT}, {"role": "user", "content": transcript}]


def merge(items_json: str) -> list[dict]:
    return [{"role": "system", "content": MERGE}, {"role": "user", "content": items_json}]
