"""Map ``[n]`` markers in an answer to the retrieved chunks they refer to."""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..vectorstore.chunk_store import ChunkRecord

_MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
# Some models ignore the requested "[1]" style and emit a browsing-style marker such as
# 【1†L00:02:05-L00:02:05】. We rewrite those to "[1]" so they become real citations.
_ALT_MARKER = re.compile(r"\u3010\s*(\d+)[^\u3011]*\u3011")
SNIPPET_CHARS = 240


@dataclass
class Citation:
    id: int
    chunk_index: int
    speaker: str
    start: str
    end: str
    text: str


def _snippet(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= SNIPPET_CHARS else text[: SNIPPET_CHARS - 1].rstrip() + "\u2026"


def normalize_markers(answer: str) -> str:
    """Rewrite non-standard citation markers (e.g. 【1†L00:02:05】) to the standard [1] form."""
    return _ALT_MARKER.sub(r"[\1]", answer)


def extract_citations(answer: str, chunks: list[ChunkRecord]) -> list[Citation]:
    seen: list[int] = []
    for match in _MARKER.finditer(answer):
        for part in match.group(1).split(","):
            n = int(part.strip())
            if 1 <= n <= len(chunks) and n not in seen:
                seen.append(n)
    citations = []
    for n in seen:
        chunk = chunks[n - 1]
        meta = chunk.metadata
        citations.append(
            Citation(
                id=n,
                chunk_index=chunk.chunk_index,
                speaker=str(meta.get("speakers", "")),
                start=str(meta.get("start_label", "")),
                end=str(meta.get("end_label", "")),
                text=_snippet(chunk.text),
            )
        )
    return citations
