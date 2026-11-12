"""Result shapes for meeting intelligence extraction."""
from __future__ import annotations

from pydantic import BaseModel


class Decision(BaseModel):
    decision: str
    speaker: str | None = None
    timestamp: str | None = None


class ActionItem(BaseModel):
    task: str
    owner: str | None = None
    due: str | None = None
    timestamp: str | None = None


class DecisionsResult(BaseModel):
    decisions: list[Decision]


class ActionItemsResult(BaseModel):
    action_items: list[ActionItem]
