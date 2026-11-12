from fastapi import APIRouter, Depends, HTTPException

from ..container import Container
from ..schemas import RetryResponse, Section, StatusResponse
from ..services import intelligence_extractor
from .deps import get_container

router = APIRouter()


@router.get("/status/{session_id}", response_model=StatusResponse)
def get_status(session_id: str, container: Container = Depends(get_container)):
    snapshot = container.session_store.snapshot(session_id)
    if snapshot is None:
        raise HTTPException(404, "Session not found.")
    return snapshot


@router.post("/session/{session_id}/intelligence/{section}/retry", response_model=RetryResponse, status_code=202)
def retry_section(session_id: str, section: Section, container: Container = Depends(get_container)):
    indexing = container.session_store.get_indexing(session_id)
    if indexing is None:
        raise HTTPException(404, "Session not found.")
    if indexing["status"] != "completed":
        raise HTTPException(409, "The transcript has not been indexed.")
    if not intelligence_extractor.retry_section(container, session_id, section):
        raise HTTPException(409, f"'{section}' can only be retried when it has failed.")
    return RetryResponse(session_id=session_id, section=section, status="processing")
