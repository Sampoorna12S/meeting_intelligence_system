from fastapi import APIRouter, Depends, HTTPException, Response

from ..container import Container
from .deps import get_container

router = APIRouter()


@router.delete("/session/{session_id}", status_code=204)
def delete_session(session_id: str, container: Container = Depends(get_container)):
    if not container.session_store.exists(session_id):
        raise HTTPException(404, "Session not found.")
    container.session_store.delete_session(session_id)  # marks deleted first so in-flight jobs stop writing
    container.chunk_store.delete_session(session_id)
    return Response(status_code=204)
