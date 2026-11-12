from __future__ import annotations

from typing import Literal

from meeting_ai.intelligence.models import ActionItem, Decision
from pydantic import BaseModel, Field

Status = Literal["pending", "processing", "completed", "failed"]
Section = Literal["summary", "decisions", "action_items"]


class UploadResponse(BaseModel):
    session_id: str
    filename: str


class IndexingState(BaseModel):
    status: Status
    stage: str | None = None
    error: str | None = None


class IntelligenceStatuses(BaseModel):
    summary: Status
    decisions: Status
    action_items: Status


class IntelligenceErrors(BaseModel):
    summary: str | None = None
    decisions: str | None = None
    action_items: str | None = None


class StatusData(BaseModel):
    summary: str | None = None
    decisions: list[Decision] = []
    action_items: list[ActionItem] = []


class StatusResponse(BaseModel):
    session_id: str
    filename: str
    indexing: IndexingState
    intelligence: IntelligenceStatuses
    errors: IntelligenceErrors
    data: StatusData


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    session_id: str
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = []


class CitationModel(BaseModel):
    id: int
    speaker: str
    start: str
    end: str
    text: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationModel]


class RetryResponse(BaseModel):
    session_id: str
    section: Section
    status: Status
