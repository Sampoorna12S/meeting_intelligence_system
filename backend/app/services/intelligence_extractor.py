"""Stage 2: summary, decisions and action items as three independent jobs."""
from __future__ import annotations

import logging

from meeting_ai.intelligence.action_items import generate_action_items
from meeting_ai.intelligence.decisions import generate_decisions
from meeting_ai.intelligence.summary import generate_summary

from ..container import Container
from ..store.session_store import SECTIONS

logger = logging.getLogger(__name__)


def _generate(container: Container, section: str, transcript: str):
    max_chars = container.ai_config.extraction_max_chars
    if section == "summary":
        return generate_summary(container.llm, transcript, max_chars)
    if section == "decisions":
        return [d.model_dump() for d in generate_decisions(container.llm, transcript, max_chars)]
    if section == "action_items":
        return [i.model_dump() for i in generate_action_items(container.llm, transcript, max_chars)]
    raise ValueError(f"Unknown section: {section}")


def _execute(container: Container, session_id: str, section: str) -> None:
    """Do the work for a section that has already been claimed (status = processing)."""
    store = container.session_store
    try:
        if store.is_deleted(session_id):
            return
        transcript = container.chunk_store.get_transcript_text(session_id)
        if not transcript.strip():
            raise ValueError("No transcript content found for this session.")
        result = _generate(container, section, transcript)
        store.set_section(session_id, section, "completed", result=result)
    except Exception as exc:
        logger.exception("Extraction '%s' failed for %s", section, session_id)
        store.set_section(session_id, section, "failed", error=str(exc)[:300] or exc.__class__.__name__)


def run_section(container: Container, session_id: str, section: str) -> None:
    """Claim (pending -> processing) and execute. A no-op if another task already owns the section."""
    if container.session_store.claim_section(session_id, section):
        _execute(container, session_id, section)


def start_all(container: Container, session_id: str) -> None:
    for section in SECTIONS:
        container.scheduler.submit(run_section, container, session_id, section)


def retry_section(container: Container, session_id: str, section: str) -> bool:
    """Re-run a failed section. Returns False if it is not in the failed state."""
    if not container.session_store.claim_section(session_id, section, allow_failed=True):
        return False
    container.scheduler.submit(_execute, container, session_id, section)
    return True
