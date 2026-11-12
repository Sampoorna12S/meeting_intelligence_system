"""Prompts for the meeting summary (single pass, per-window and merge)."""
from __future__ import annotations

SINGLE = """TASK: SUMMARY
Summarise the meeting transcript in 1-2 short paragraphs (at most about 150 words): what the meeting was about, the main points discussed and the outcome.
Use only the transcript. Plain text, no headings, no bullet points."""

PART = """TASK: SUMMARY_PART
This is part {i} of {n} of a long meeting transcript. Summarise the key points of this part in at most 120 words.
Use only the text provided. Plain text."""

MERGE = """TASK: SUMMARY_MERGE
Below are summaries of consecutive parts of one meeting. Merge them into a single coherent summary of 1-2 short paragraphs (at most about 150 words).
Use only the text provided. Plain text, no headings."""


def single(transcript: str) -> list[dict]:
    return [{"role": "system", "content": SINGLE}, {"role": "user", "content": transcript}]


def part(window: str, i: int, n: int) -> list[dict]:
    return [{"role": "system", "content": PART.format(i=i, n=n)}, {"role": "user", "content": window}]


def merge(text: str) -> list[dict]:
    return [{"role": "system", "content": MERGE}, {"role": "user", "content": text}]
