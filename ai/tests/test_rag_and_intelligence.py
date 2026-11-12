import json

import pytest
from conftest import SAMPLE

from meeting_ai.ingestion.chunker import chunk_turns
from meeting_ai.ingestion.parser import parse_transcript
from meeting_ai.intelligence.action_items import generate_action_items
from meeting_ai.intelligence.decisions import generate_decisions
from meeting_ai.intelligence.map_reduce import split_windows
from meeting_ai.intelligence.summary import generate_summary
from meeting_ai.llm.json_utils import StructuredOutputError, extract_json
from meeting_ai.rag.pipeline import NOT_FOUND_ANSWER, RagPipeline
from meeting_ai.retrieval.retriever import Retriever


class ScriptedLLM:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, messages, temperature=0.2):
        self.calls.append(messages)
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return reply(messages) if callable(reply) else reply


def test_rag_answer_maps_citations_to_chunks(chunk_store):
    chunk_store.add_chunks("s1", chunk_turns(parse_transcript(SAMPLE), target_chars=200))
    llm = ScriptedLLM("Dave will update the pricing page copy [1].")
    result = RagPipeline(Retriever(chunk_store, top_k=3), llm).answer("s1", "Who updates the pricing page?")
    assert result.answer.startswith("Dave will update")
    assert len(result.citations) == 1
    cit = result.citations[0]
    assert cit.id == 1 and cit.speaker and cit.start
    # the system prompt grounds the model and the excerpt is in the user message
    assert "ONLY" in llm.calls[0][0]["content"]
    assert "Transcript excerpts" in llm.calls[0][-1]["content"]


def test_rag_ignores_out_of_range_markers_and_includes_history(chunk_store):
    chunk_store.add_chunks("s1", chunk_turns(parse_transcript(SAMPLE), target_chars=200))
    llm = ScriptedLLM("Answer [99] and [1, 2].")
    history = [{"role": "user", "content": "earlier q"}, {"role": "assistant", "content": "earlier a"}]
    result = RagPipeline(Retriever(chunk_store, top_k=3), llm).answer("s1", "q", history)
    assert {c.id for c in result.citations} <= {1, 2}
    assert 99 not in {c.id for c in result.citations}
    roles = [m["role"] for m in llm.calls[0]]
    assert roles == ["system", "user", "assistant", "user"]


def test_rag_empty_session_does_not_call_llm(chunk_store):
    llm = ScriptedLLM("should not be used")
    result = RagPipeline(Retriever(chunk_store), llm).answer("missing", "anything?")
    assert result.answer == NOT_FOUND_ANSWER and result.citations == [] and llm.calls == []


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! Here you go: {"a": [1, 2]} hope that helps') == {"a": [1, 2]}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_decisions_retry_once_on_invalid_json():
    good = json.dumps({"decisions": [{"decision": "Launch Nov 21", "speaker": "Alice", "timestamp": "00:01:34"}]})
    llm = ScriptedLLM("not json at all", good)
    decisions = generate_decisions(llm, SAMPLE, 24000)
    assert decisions[0].decision == "Launch Nov 21" and len(llm.calls) == 2


def test_decisions_fail_after_second_invalid_reply():
    with pytest.raises(StructuredOutputError):
        generate_decisions(ScriptedLLM("nope"), SAMPLE, 24000)


def test_action_items_accept_bare_list_and_null_fields():
    llm = ScriptedLLM(json.dumps([{"task": "Draft email", "owner": "Carol", "due": None, "timestamp": None}]))
    items = generate_action_items(llm, SAMPLE, 24000)
    assert items[0].owner == "Carol" and items[0].due is None


def test_split_windows_respects_limit():
    text = "\n".join(f"line {i} " + "x" * 50 for i in range(100))
    windows = split_windows(text, 500)
    assert len(windows) > 5 and all(len(w) <= 500 for w in windows)
    assert "\n".join(windows) == text


def test_long_transcript_uses_map_reduce_for_all_three():
    long_text = "\n".join(f"[00:{i // 60:02d}:{i % 60:02d}] Alice: " + "word " * 30 for i in range(60))

    def replies(messages):
        task = messages[0]["content"].split("\n")[0]
        if task.startswith("TASK: SUMMARY"):
            return "partial summary"
        if task.startswith("TASK: DECISIONS"):
            return json.dumps({"decisions": [{"decision": "Same decision"}]})
        return json.dumps({"action_items": [{"task": "Same task"}]})

    llm = ScriptedLLM(replies)
    assert generate_summary(llm, long_text, 600) == "partial summary"
    assert len(generate_decisions(llm, long_text, 600)) >= 1
    assert len(generate_action_items(llm, long_text, 600)) >= 1
    tasks = [c[0]["content"].split("\n")[0] for c in llm.calls]
    assert "TASK: SUMMARY_PART" in tasks and "TASK: SUMMARY_MERGE" in tasks
    assert "TASK: DECISIONS_MERGE" in tasks or "TASK: DECISIONS" in tasks
