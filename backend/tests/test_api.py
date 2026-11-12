import threading
import time

from conftest import SAMPLE, SECTIONS, all_sections_terminal, upload, wait_for

from app.services import intelligence_extractor


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


# ---------- upload validation ----------
def test_upload_rejects_wrong_extension(client):
    assert upload(client, name="notes.pdf").status_code == 400


def test_upload_rejects_empty_and_unparseable(client):
    assert upload(client, content="   \n").status_code == 400
    r = upload(client, content="this has no speakers at all")
    assert r.status_code == 400 and "speaker" in r.json()["detail"].lower()


def test_upload_rejects_non_utf8(client):
    r = client.post("/api/upload", files={"file": ("a.txt", b"\xff\xfe\x00bad", "text/plain")})
    assert r.status_code == 400


def test_upload_rejects_too_large(client, container):
    container.settings.max_upload_mb = 0.0001
    assert upload(client).status_code == 413


# ---------- indexing + status ----------
def test_upload_indexes_and_all_sections_complete(client):
    r = upload(client)
    assert r.status_code == 202
    sid = r.json()["session_id"]
    assert r.json()["filename"] == "meeting.txt"

    body = wait_for(client, sid, all_sections_terminal)
    assert body["indexing"]["status"] == "completed"
    assert body["filename"] == "meeting.txt"
    assert body["intelligence"] == {s: "completed" for s in SECTIONS}
    assert body["data"]["summary"] == "The team agreed on a launch date."
    assert body["data"]["decisions"][0]["decision"] == "Launch on November 21st"
    assert body["data"]["action_items"][0]["owner"] == "Dave"


def test_status_unknown_session(client):
    assert client.get("/api/status/nope").status_code == 404


def test_indexing_failure_is_reported_and_blocks_chat(client, container, monkeypatch):
    def boom(texts):
        raise RuntimeError("embedding exploded")

    monkeypatch.setattr(container.embedder, "embed_documents", boom)
    sid = upload(client).json()["session_id"]
    body = client.get(f"/api/status/{sid}").json()
    assert body["indexing"]["status"] == "failed" and "embedding exploded" in body["indexing"]["error"]
    assert container.chunk_store.count(sid) == 0
    r = client.post("/api/chat", json={"session_id": sid, "question": "hi"})
    assert r.status_code == 409
    time.sleep(0.2)
    assert container.llm.calls == []  # extraction never started


# ---------- chat ----------
def test_chat_works_while_extraction_is_still_running(client, llm):
    llm.gate = threading.Event()
    try:
        sid = upload(client).json()["session_id"]
        body = client.get(f"/api/status/{sid}").json()
        assert body["indexing"]["status"] == "completed"
        wait_for(client, sid, lambda b: b["intelligence"]["summary"] == "processing")
        assert body["data"]["summary"] is None

        r = client.post("/api/chat", json={"session_id": sid, "question": "Who updates the pricing page?"})
        assert r.status_code == 200
        data = r.json()
        assert "pricing" in data["answer"].lower()
        assert data["citations"] and data["citations"][0]["speaker"]
        assert data["citations"][0]["start"].startswith("00:")
        # still not done: chat did not wait for extraction
        assert not all_sections_terminal(client.get(f"/api/status/{sid}").json())
    finally:
        llm.gate.set()
    wait_for(client, sid, all_sections_terminal)


def test_chat_unknown_session_and_not_ready(client, container):
    assert client.post("/api/chat", json={"session_id": "nope", "question": "hi"}).status_code == 404
    container.session_store.create_session("pending_one", "x.txt")  # indexing still pending
    assert client.post("/api/chat", json={"session_id": "pending_one", "question": "hi"}).status_code == 409


def test_chat_validates_question(client):
    sid = upload(client).json()["session_id"]
    assert client.post("/api/chat", json={"session_id": sid, "question": ""}).status_code == 422


def test_chat_history_is_capped(client, llm):
    sid = upload(client).json()["session_id"]
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(10)]
    assert client.post("/api/chat", json={"session_id": sid, "question": "q", "history": history}).status_code == 200
    msgs = llm.chat_messages[-1]
    assert len(msgs) == 1 + 6 + 1 and msgs[1]["content"] == "m4"


def test_chat_llm_failure_returns_502(client, container, monkeypatch):
    from meeting_ai.llm.client import LLMError

    sid = upload(client).json()["session_id"]

    def boom(*a, **k):
        raise LLMError("provider down")

    monkeypatch.setattr(container.rag._llm, "complete", boom)
    r = client.post("/api/chat", json={"session_id": sid, "question": "q"})
    assert r.status_code == 502 and "provider down" in r.json()["detail"]


# ---------- failure isolation, retry, duplicates ----------
def test_one_failed_section_does_not_affect_others_or_chat(client, llm):
    llm.fail.add("decisions")
    sid = upload(client).json()["session_id"]
    body = wait_for(client, sid, all_sections_terminal)
    assert body["intelligence"] == {"summary": "completed", "decisions": "failed", "action_items": "completed"}
    assert "simulated LLM failure" in body["errors"]["decisions"]
    assert body["data"]["decisions"] == [] and body["data"]["summary"]
    assert client.post("/api/chat", json={"session_id": sid, "question": "q"}).status_code == 200


def test_retry_failed_section(client, llm):
    llm.fail.add("decisions")
    sid = upload(client).json()["session_id"]
    wait_for(client, sid, all_sections_terminal)

    llm.fail.clear()
    r = client.post(f"/api/session/{sid}/intelligence/decisions/retry")
    assert r.status_code == 202 and r.json()["status"] == "processing"
    body = wait_for(client, sid, lambda b: b["intelligence"]["decisions"] == "completed")
    assert body["data"]["decisions"][0]["speaker"] == "Alice"
    assert body["errors"]["decisions"] is None


def test_retry_rules(client, llm):
    sid = upload(client).json()["session_id"]
    wait_for(client, sid, all_sections_terminal)
    assert client.post(f"/api/session/{sid}/intelligence/summary/retry").status_code == 409  # not failed
    assert client.post("/api/session/nope/intelligence/summary/retry").status_code == 404
    assert client.post(f"/api/session/{sid}/intelligence/bogus/retry").status_code == 422


def test_no_duplicate_extraction(client, llm, container):
    sid = upload(client).json()["session_id"]
    wait_for(client, sid, all_sections_terminal)
    before = llm.count("TASK: SUMMARY")
    # triggering extraction again must be a no-op: the sections are already owned/finished
    intelligence_extractor.start_all(container, sid)
    intelligence_extractor.run_section(container, sid, "summary")
    time.sleep(0.3)
    assert llm.count("TASK: SUMMARY") == before


def test_claim_is_exclusive_under_concurrency(container):
    store = container.session_store
    store.create_session("s", "f.txt")
    results = []
    threads = [threading.Thread(target=lambda: results.append(store.claim_section("s", "summary"))) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count(True) == 1


# ---------- delete ----------
def test_delete_removes_everything(client, container):
    sid = upload(client).json()["session_id"]
    wait_for(client, sid, all_sections_terminal)
    assert container.chunk_store.count(sid) > 0
    assert client.delete(f"/api/session/{sid}").status_code == 204
    assert client.get(f"/api/status/{sid}").status_code == 404
    assert container.chunk_store.count(sid) == 0
    assert container.session_store._col.get(where={"session_id": sid})["ids"] == []
    assert client.delete(f"/api/session/{sid}").status_code == 404
    assert client.post("/api/chat", json={"session_id": sid, "question": "q"}).status_code == 404


def test_delete_while_extraction_running_leaves_nothing_behind(client, container, llm):
    llm.gate = threading.Event()
    sid = upload(client).json()["session_id"]
    wait_for(client, sid, lambda b: b["intelligence"]["summary"] == "processing")
    assert client.delete(f"/api/session/{sid}").status_code == 204
    llm.gate.set()  # in-flight jobs now finish and try to save
    time.sleep(0.5)
    assert client.get(f"/api/status/{sid}").status_code == 404
    assert container.session_store._col.get(where={"session_id": sid})["ids"] == []
    assert container.chunk_store.count(sid) == 0


# ---------- restart recovery ----------
def test_stale_jobs_are_failed_on_startup(container):
    store = container.session_store
    # session A crashed mid-indexing
    store.create_session("a", "a.txt")
    store.set_indexing("a", "processing", stage="embedding")
    # session B was indexed, extraction was interrupted
    store.create_session("b", "b.txt")
    store.set_indexing("b", "completed")
    store.set_section("b", "summary", "completed", result="done")
    store.set_section("b", "decisions", "processing")
    # action_items stays pending

    assert store.mark_stale_processing_failed() >= 3
    a, b = store.snapshot("a"), store.snapshot("b")
    assert a["indexing"]["status"] == "failed" and "restart" in a["indexing"]["error"]
    assert b["intelligence"] == {"summary": "completed", "decisions": "failed", "action_items": "failed"}
    assert b["data"]["summary"] == "done"
