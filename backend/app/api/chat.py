import logging

from fastapi import APIRouter, Depends, HTTPException
from meeting_ai.llm.client import LLMError

from ..container import Container
from ..schemas import ChatRequest, ChatResponse, CitationModel
from ..services.chat_service import IndexingNotReady, SessionNotFound, answer_question
from .deps import get_container

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, container: Container = Depends(get_container)):
    history = [m.model_dump() for m in req.history]
    try:
        answer = answer_question(container, req.session_id, req.question.strip(), history)
    except SessionNotFound:
        raise HTTPException(404, "Session not found.")
    except IndexingNotReady:
        raise HTTPException(409, "The transcript is still being indexed (or indexing failed).")
    except LLMError as exc:
        logger.warning("LLM error during chat: %s", exc)
        raise HTTPException(502, str(exc))
    return ChatResponse(
        answer=answer.answer,
        citations=[
            CitationModel(id=c.id, speaker=c.speaker, start=c.start, end=c.end, text=c.text)
            for c in answer.citations
        ],
    )
