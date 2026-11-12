from conftest import SAMPLE

from meeting_ai.ingestion.chunker import chunk_turns
from meeting_ai.ingestion.parser import parse_transcript
from meeting_ai.retrieval.retriever import Retriever


def _index(store, sid, target=200):
    chunks = chunk_turns(parse_transcript(SAMPLE), target_chars=target)
    store.add_chunks(sid, chunks)
    return chunks


def test_add_query_and_session_isolation(chunk_store):
    chunks = _index(chunk_store, "s1")
    _index(chunk_store, "s2")
    assert chunk_store.count("s1") == len(chunks)
    hits = chunk_store.query("s1", "pricing page copy", top_k=2)
    assert hits and all(h.metadata["session_id"] == "s1" for h in hits)
    assert "pricing" in hits[0].text.lower()


def test_retriever_returns_meeting_order(chunk_store):
    _index(chunk_store, "s1")
    recs = Retriever(chunk_store, top_k=4).retrieve("s1", "announcement email and pricing")
    idx = [r.chunk_index for r in recs]
    assert idx == sorted(idx)


def test_transcript_rebuild_has_no_duplicates(chunk_store):
    _index(chunk_store, "s1", target=150)
    text = chunk_store.get_transcript_text("s1")
    assert text.split("\n") == SAMPLE.strip().split("\n")


def test_delete_session_removes_only_that_session(chunk_store):
    _index(chunk_store, "s1")
    _index(chunk_store, "s2")
    chunk_store.delete_session("s1")
    assert chunk_store.count("s1") == 0
    assert chunk_store.count("s2") > 0
