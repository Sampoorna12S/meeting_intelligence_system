"""Transcript parsing: raw ``.txt`` content -> a list of speaker turns.

Supported line formats (the most common one in the file wins):

    [00:01:23] Alice: text          bracketed timestamp
    Alice (00:01:23): text          timestamp in parentheses
    00:01:23 Alice: text            leading timestamp
    Alice: text                     no timestamps

Lines that don't start a new turn are appended to the previous turn.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


class TranscriptParseError(ValueError):
    """Raised when no speaker turns can be found in the transcript."""


@dataclass
class Turn:
    index: int
    speaker: str
    text: str
    seconds: int | None = None
    label: str | None = None  # normalised HH:MM:SS


_TS = r"\d{1,2}:\d{2}(?::\d{2})?"
_SPEAKER = r"[^\W\d_][\w .'\-]{0,38}?"

_PATTERNS: list[re.Pattern[str]] = [
    re.compile(rf"^\s*\[(?P<ts>{_TS})\]\s*(?P<speaker>{_SPEAKER})\s*:\s*(?P<text>.*)$"),
    re.compile(rf"^\s*(?P<speaker>{_SPEAKER})\s*\(\s*(?P<ts>{_TS})\s*\)\s*:\s*(?P<text>.*)$"),
    re.compile(rf"^\s*(?P<ts>{_TS})\s+(?P<speaker>{_SPEAKER})\s*:\s*(?P<text>.*)$"),
    re.compile(rf"^\s*(?P<speaker>{_SPEAKER})\s*:\s*(?P<text>.*)$"),
]

_MAX_SPEAKER_WORDS = 4


def _to_seconds(ts: str) -> int:
    parts = [int(p) for p in ts.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def format_timestamp(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _match(pattern: re.Pattern[str], line: str) -> tuple[str, str | None, str] | None:
    m = pattern.match(line)
    if not m:
        return None
    speaker = " ".join(m.group("speaker").split())
    if not speaker or len(speaker.split()) > _MAX_SPEAKER_WORDS:
        return None
    ts = m.groupdict().get("ts")
    return speaker, ts, m.group("text").strip()


def parse_transcript(text: str) -> list[Turn]:
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    counts = [sum(1 for ln in lines if _match(p, ln)) for p in _PATTERNS]
    best = max(range(len(_PATTERNS)), key=lambda i: counts[i])
    if counts[best] == 0:
        raise TranscriptParseError(
            "No speaker turns found. Expected lines like '[00:01:23] Alice: text', "
            "'Alice (00:01:23): text' or 'Alice: text'."
        )
    pattern = _PATTERNS[best]

    turns: list[Turn] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        parsed = _match(pattern, line)
        if parsed:
            speaker, ts, body = parsed
            seconds = _to_seconds(ts) if ts else None
            turns.append(
                Turn(
                    index=len(turns),
                    speaker=speaker,
                    text=body,
                    seconds=seconds,
                    label=format_timestamp(seconds) if seconds is not None else None,
                )
            )
        elif turns:
            turns[-1].text = f"{turns[-1].text} {stripped}".strip()
        # lines before the first turn (titles, headers) are ignored

    turns = [t for t in turns if t.text]
    for i, t in enumerate(turns):
        t.index = i
    if not turns:
        raise TranscriptParseError("The transcript contains speaker names but no spoken text.")
    return turns
