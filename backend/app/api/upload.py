import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from ..container import Container
from ..schemas import UploadResponse
from ..services.processing_service import run_indexing, validate_and_parse
from .deps import get_container

router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    container: Container = Depends(get_container),
):
    filename = file.filename or "transcript.txt"
    if not filename.lower().endswith(".txt"):
        raise HTTPException(400, "Only .txt transcript files are supported.")

    max_bytes = int(container.settings.max_upload_mb * 1024 * 1024)
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, f"The file is larger than the {container.settings.max_upload_mb:g} MB limit.")

    try:
        turns = validate_and_parse(content)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    session_id = f"session_{uuid.uuid4().hex[:12]}"
    container.session_store.create_session(session_id, filename)
    background_tasks.add_task(run_indexing, container, session_id, turns)
    return UploadResponse(session_id=session_id, filename=filename)
