import hashlib
import math
import re
import threading
import time

import chromadb
import pytest
from chromadb.config import Settings as ChromaSettings
from fastapi.testclient import TestClient
from meeting_ai.config import AIConfig
from meeting_ai.llm.client import LLMError

from app.config import Settings
from app.container import Container
from app.main import create_app

SAMPLE = """[00:00:05] Alice: Welcome everyone. Today we decide the launch date.
[00:00:20] Bob: Engineering is ready. Export might slip by a week.
[00:00:40] Alice: Launch without export then. We launch on November 21st.
[00:01:10] Carol: I will draft the customer announcement email by Friday.
[00:01:30] Dave: I will update the pricing page copy by next Wednesday.
"""

SECTIONS = ("summary", "decisions", "action_items")


class FakeEmbedder:
    dim = 128

    def _vec(self, text):
        v = [0.0] * self.dim
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            v[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class FakeLLM:
    """Answers by prompt type. Sections can be made to fail or to block on a gate."""

    def __init__(self):
        self.fail: set[str] = set()
        self.gate: threading.Event | None = None
        self.calls: list[str] = []
        self.chat_messages: list[list[dict]] = []

    def complete(self, messages, temperature=0.2):
        task = messages[0]["content"].split("\n")[0]
        self.calls.append(task)
        if task == "TASK: MEETING_QA":
            self.chat_messages.append(messages)
            return "Dave will update the pricing page copy [1]."
        section = (
            "summary" if task.startswith("TASK: SUMMARY") else "decisions" if task.startswith("TASK: DECISIONS") else "action_items"
        )
        if self.gate is not None:
            self.gate.wait(10)
        if section in self.fail:
            raise LLMError("simulated LLM failure")
        if section == "summary":
            return "The team agreed on a launch date."
        if section == "decisions":
            return '{"decisions": [{"decision": "Launch on November 21st", "speaker": "Alice", "timestamp": "00:00:40"}]}'
        return '{"action_items": [{"task": "Update pricing page copy", "owner": "Dave", "due": "next Wednesday", "timestamp": "00:01:30"}]}'

    def count(self, prefix):
        return sum(1 for c in self.calls if c.startswith(prefix))


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def container(tmp_path, llm):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"), settings=ChromaSettings(anonymized_telemetry=False))
    settings = Settings(_env_file=None, extraction_concurrency=3)
    return Container(settings, AIConfig(), embedder=FakeEmbedder(), llm=llm, chroma_client=client)


@pytest.fixture
def client(container):
    app = create_app(container_factory=lambda: container)
    with TestClient(app) as c:
        yield c


def upload(client, content=SAMPLE, name="meeting.txt"):
    return client.post("/api/upload", files={"file": (name, content.encode(), "text/plain")})


def wait_for(client, session_id, predicate, timeout=8.0):
    deadline = time.time() + timeout
    body = None
    while time.time() < deadline:
        body = client.get(f"/api/status/{session_id}").json()
        if predicate(body):
            return body
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting; last status: {body}")


def all_sections_terminal(body):
    return all(body["intelligence"][s] in ("completed", "failed") for s in SECTIONS)
