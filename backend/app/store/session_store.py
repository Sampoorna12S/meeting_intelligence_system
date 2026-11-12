"""Session, status and result storage, kept in ChromaDB.

One record per concern (meta, indexing, summary, decisions, action_items) so concurrent
jobs never overwrite each other. Records are only fetched by id or ``where`` filter;
a constant dummy embedding is stored because ChromaDB requires one.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any

COLLECTION = "meeting_sessions"
SECTIONS = ("summary", "decisions", "action_items")
_DUMMY_EMBEDDING = [0.0]
INTERRUPTED = "Interrupted by a server restart."


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionStore:
    def __init__(self, client):
        self._col = client.get_or_create_collection(COLLECTION)
        self._lock = threading.RLock()
        self._deleted: set[str] = set()

    # ---- low level (callers hold the lock) ----
    @staticmethod
    def _rid(session_id: str, kind: str) -> str:
        return f"{session_id}:{kind}"

    def _put(self, session_id: str, kind: str, payload: dict, status: str | None = None) -> None:
        meta: dict[str, Any] = {"session_id": session_id, "kind": kind, "updated_at": _now()}
        if status:
            meta["status"] = status
        self._col.upsert(
            ids=[self._rid(session_id, kind)],
            documents=[json.dumps(payload, ensure_ascii=False)],
            metadatas=[meta],
            embeddings=[_DUMMY_EMBEDDING],
        )

    def _get(self, session_id: str, kind: str) -> tuple[dict, dict] | None:
        res = self._col.get(ids=[self._rid(session_id, kind)], include=["documents", "metadatas"])
        if not res["ids"]:
            return None
        return json.loads(res["documents"][0]), res["metadatas"][0]

    def _alive(self, session_id: str) -> bool:
        return session_id not in self._deleted and self._get(session_id, "meta") is not None

    # ---- lifecycle ----
    def create_session(self, session_id: str, filename: str) -> None:
        with self._lock:
            self._put(session_id, "meta", {"filename": filename, "created_at": _now(), "chunk_count": 0})
            self._put(session_id, "indexing", {"stage": None, "error": None}, "pending")
            for section in SECTIONS:
                self._put(session_id, section, {"result": None, "error": None}, "pending")

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return self._alive(session_id)

    def is_deleted(self, session_id: str) -> bool:
        return session_id in self._deleted

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            self._deleted.add(session_id)
            self._col.delete(where={"session_id": session_id})

    # ---- indexing ----
    def set_indexing(self, session_id: str, status: str, stage: str | None = None, error: str | None = None) -> bool:
        with self._lock:
            if not self._alive(session_id):
                return False
            self._put(session_id, "indexing", {"stage": stage, "error": error}, status)
            return True

    def set_chunk_count(self, session_id: str, count: int) -> None:
        with self._lock:
            found = self._get(session_id, "meta")
            if found and session_id not in self._deleted:
                payload, _ = found
                payload["chunk_count"] = count
                self._put(session_id, "meta", payload)

    def get_indexing(self, session_id: str) -> dict | None:
        with self._lock:
            if not self._alive(session_id):
                return None
            payload, meta = self._get(session_id, "indexing")
            return {"status": meta.get("status", "pending"), "stage": payload.get("stage"), "error": payload.get("error")}

    # ---- intelligence sections ----
    def set_section(self, session_id: str, section: str, status: str, result: Any = None, error: str | None = None) -> bool:
        with self._lock:
            if not self._alive(session_id):
                return False
            self._put(session_id, section, {"result": result, "error": error}, status)
            return True

    def get_section_status(self, session_id: str, section: str) -> str | None:
        with self._lock:
            found = self._get(session_id, section)
            return found[1].get("status") if found else None

    def claim_section(self, session_id: str, section: str, allow_failed: bool = False) -> bool:
        """Atomically move a section to ``processing``; False if someone else already owns it."""
        with self._lock:
            if not self._alive(session_id):
                return False
            found = self._get(session_id, section)
            if not found:
                return False
            status = found[1].get("status")
            if status == "pending" or (allow_failed and status == "failed"):
                self._put(session_id, section, {"result": None, "error": None}, "processing")
                return True
            return False

    # ---- reads for the API ----
    def snapshot(self, session_id: str) -> dict | None:
        with self._lock:
            if session_id in self._deleted:
                return None
            res = self._col.get(where={"session_id": session_id}, include=["documents", "metadatas"])
        records: dict[str, tuple[dict, dict]] = {}
        for doc, meta in zip(res["documents"], res["metadatas"]):
            records[meta["kind"]] = (json.loads(doc), meta)
        if "meta" not in records:
            return None

        idx_payload, idx_meta = records.get("indexing", ({}, {}))
        intelligence, errors, data = {}, {}, {"summary": None, "decisions": [], "action_items": []}
        for section in SECTIONS:
            payload, meta = records.get(section, ({}, {}))
            status = meta.get("status", "pending")
            intelligence[section] = status
            errors[section] = payload.get("error") if status == "failed" else None
            if status == "completed" and payload.get("result") is not None:
                data[section] = payload["result"]
        return {
            "session_id": session_id,
            "filename": records["meta"][0].get("filename", ""),
            "indexing": {
                "status": idx_meta.get("status", "pending"),
                "stage": idx_payload.get("stage"),
                "error": idx_payload.get("error"),
            },
            "intelligence": intelligence,
            "errors": errors,
            "data": data,
        }

    # ---- startup recovery ----
    def mark_stale_processing_failed(self) -> int:
        """After a restart nothing can still be running: fail anything left pending/processing."""
        fixed = 0
        with self._lock:
            res = self._col.get(
                where={"status": {"$in": ["pending", "processing"]}}, include=["documents", "metadatas"]
            )
            rows = [(json.loads(d), m) for d, m in zip(res["documents"], res["metadatas"])]
            for payload, meta in rows:
                if meta.get("kind") == "indexing":
                    self._put(meta["session_id"], "indexing", {"stage": None, "error": INTERRUPTED}, "failed")
                    fixed += 1
            for payload, meta in rows:
                kind, sid = meta.get("kind"), meta.get("session_id")
                if kind in SECTIONS:
                    indexing = self._get(sid, "indexing")
                    # only sections of fully indexed sessions can be retried; others stay as they are
                    if indexing and indexing[1].get("status") == "completed":
                        self._put(sid, kind, {"result": None, "error": INTERRUPTED}, "failed")
                        fixed += 1
        return fixed
