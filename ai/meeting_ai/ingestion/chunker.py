"""Speaker-aware chunking.

* Adjacent turns by the same speaker are merged.
* Turns are never split unless a single turn is longer than the target size
  (then it is split on sentence boundaries).
* Consecutive chunks overlap by ``overlap_turns`` lines for context continuity.
* Every chunk is one line per turn: ``[HH:MM:SS] Speaker: text``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .parser import Turn

DEFAULT_TARGET_CHARS = 800
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    index: int
    text: str
    speakers: list[str]
    start_seconds: int
    end_seconds: int
    start_label: str
    end_label: str
    turn_start: int
    turn_end: int
    overlap_lines: int  # leading lines repeated from the previous chunk

    def metadata(self, session_id: str) -> dict:
        """Scalar-only metadata, as ChromaDB requires."""
        return {
            "session_id": session_id,
            "chunk_index": self.index,
            "speakers": ", ".join(self.speakers),
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "start_label": self.start_label,
            "end_label": self.end_label,
            "turn_start": self.turn_start,
            "turn_end": self.turn_end,
            "overlap_lines": self.overlap_lines,
        }


@dataclass
class _Piece:
    turn_index: int
    speaker: str
    line: str
    start_seconds: int | None
    start_label: str | None
    end_seconds: int | None
    end_label: str | None


def _prefix(speaker: str, label: str | None) -> str:
    return f"[{label}] {speaker}: " if label else f"{speaker}: "


def _split_text(text: str, limit: int) -> list[str]:
    limit = max(limit, 200)
    parts: list[str] = []
    current = ""
    for sentence in _SENTENCE_SPLIT.split(text):
        while len(sentence) > limit:  # a single very long sentence: split on words
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            if current:
                parts.append(current)
                current = ""
            parts.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if current and len(current) + 1 + len(sentence) > limit:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return [p for p in parts if p]


def _to_pieces(turns: list[Turn], target_chars: int) -> list[_Piece]:
    merged: list[dict] = []
    for t in turns:
        if merged and merged[-1]["speaker"] == t.speaker:
            m = merged[-1]
            m["text"] = f"{m['text']} {t.text}"
            if t.seconds is not None:
                m["end_seconds"], m["end_label"] = t.seconds, t.label
        else:
            merged.append(
                {
                    "speaker": t.speaker,
                    "text": t.text,
                    "start_seconds": t.seconds,
                    "start_label": t.label,
                    "end_seconds": t.seconds,
                    "end_label": t.label,
                }
            )

    pieces: list[_Piece] = []
    for idx, m in enumerate(merged):
        prefix = _prefix(m["speaker"], m["start_label"])
        texts = [m["text"]]
        if len(prefix) + len(m["text"]) > target_chars:
            texts = _split_text(m["text"], target_chars - len(prefix))
        for text in texts:
            pieces.append(
                _Piece(
                    turn_index=idx,
                    speaker=m["speaker"],
                    line=prefix + text,
                    start_seconds=m["start_seconds"],
                    start_label=m["start_label"],
                    end_seconds=m["end_seconds"],
                    end_label=m["end_label"],
                )
            )
    return pieces


def _build(index: int, group: list[_Piece], overlap_lines: int) -> Chunk:
    speakers: list[str] = []
    for p in group:
        if p.speaker not in speakers:
            speakers.append(p.speaker)
    first = next((p for p in group if p.start_seconds is not None), None)
    last = next((p for p in reversed(group) if p.end_seconds is not None), None)
    return Chunk(
        index=index,
        text="\n".join(p.line for p in group),
        speakers=speakers,
        start_seconds=first.start_seconds if first else -1,
        end_seconds=last.end_seconds if last else -1,
        start_label=(first.start_label or "") if first else "",
        end_label=(last.end_label or "") if last else "",
        turn_start=group[0].turn_index,
        turn_end=group[-1].turn_index,
        overlap_lines=overlap_lines,
    )


def chunk_turns(
    turns: list[Turn],
    target_chars: int = DEFAULT_TARGET_CHARS,
    overlap_turns: int = 1,
) -> list[Chunk]:
    pieces = _to_pieces(turns, target_chars)
    n = len(pieces)
    chunks: list[Chunk] = []
    start = 0
    prev_end = 0
    while start < n:
        overlap_lines = max(0, prev_end - start)
        end, size = start, 0
        while end < n:
            length = len(pieces[end].line) + 1
            # always include at least one new (non-overlap) piece so we make progress
            if end >= start + overlap_lines + 1 and size + length > target_chars:
                break
            size += length
            end += 1
        chunks.append(_build(len(chunks), pieces[start:end], overlap_lines))
        if end >= n:
            break
        prev_end = end
        start = end - overlap_turns if (end - start) > overlap_turns else end
    return chunks
