"""Prompt for grounded question answering over transcript excerpts."""
from __future__ import annotations

TASK = "TASK: MEETING_QA"

SYSTEM = f"""{TASK}
You answer questions about a meeting using ONLY the numbered transcript excerpts provided.

Rules:
- Use only information that appears in the excerpts. Do not use outside knowledge.
- If the excerpts do not contain the answer, say you could not find it in the transcript.
- After each claim, cite the supporting excerpt numbers in plain square brackets, e.g. [1] or [2][3]. Use exactly this format and no other citation style.
- Be concise. Mention speakers by name when it matters.
- Never invent speakers, timestamps, names or numbers."""


def build_messages(question: str, excerpts: list[str], history: list[dict] | None = None) -> list[dict]:
    context = "\n\n".join(excerpts)
    messages: list[dict] = [{"role": "system", "content": SYSTEM}]
    for turn in history or []:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append(
        {
            "role": "user",
            "content": f"Transcript excerpts:\n\n{context}\n\nQuestion: {question}",
        }
    )
    return messages
