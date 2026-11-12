"""Command line smoke test for the AI layer.

    python -m meeting_ai.cli index samples/sample_meeting.txt --session demo
    python -m meeting_ai.cli ask demo "Who owns the pricing page?"
    python -m meeting_ai.cli extract demo
    python -m meeting_ai.cli delete demo
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from .config import AIConfig
from .embeddings.embedder import Embedder
from .ingestion.chunker import chunk_turns
from .ingestion.parser import TranscriptParseError, parse_transcript
from .intelligence.action_items import generate_action_items
from .intelligence.decisions import generate_decisions
from .intelligence.summary import generate_summary
from .llm.client import LLMClient, LLMError
from .rag.pipeline import RagPipeline
from .retrieval.retriever import Retriever
from .vectorstore.chroma_client import get_chroma_client
from .vectorstore.chunk_store import ChunkStore


def _build(cfg: AIConfig):
    store = ChunkStore(get_chroma_client(cfg.chroma_path), Embedder(cfg.embedding_model))
    return store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="meeting_ai")
    sub = parser.add_subparsers(dest="command", required=True)
    p_index = sub.add_parser("index", help="parse, chunk, embed and store a transcript")
    p_index.add_argument("file")
    p_index.add_argument("--session", default=None)
    p_ask = sub.add_parser("ask", help="ask a question about an indexed transcript")
    p_ask.add_argument("session")
    p_ask.add_argument("question")
    p_ext = sub.add_parser("extract", help="generate summary, decisions and action items")
    p_ext.add_argument("session")
    p_del = sub.add_parser("delete", help="remove a session's chunks")
    p_del.add_argument("session")
    args = parser.parse_args(argv)

    cfg = AIConfig.from_env()
    store = _build(cfg)
    try:
        if args.command == "index":
            text = Path(args.file).read_text(encoding="utf-8-sig")
            turns = parse_transcript(text)
            chunks = chunk_turns(turns)
            session = args.session or f"session_{uuid.uuid4().hex[:12]}"
            store.add_chunks(session, chunks)
            print(f"Indexed {len(turns)} turns as {len(chunks)} chunks. Session: {session}")
        elif args.command == "ask":
            rag = RagPipeline(Retriever(store, cfg.retrieval_top_k), LLMClient(cfg))
            result = rag.answer(args.session, args.question)
            print(result.answer)
            for c in result.citations:
                print(f"  [{c.id}] {c.speaker} {c.start}-{c.end}: {c.text}")
        elif args.command == "extract":
            llm = LLMClient(cfg)
            transcript = store.get_transcript_text(args.session)
            if not transcript:
                print("No transcript found for that session.", file=sys.stderr)
                return 1
            print("SUMMARY\n", generate_summary(llm, transcript, cfg.extraction_max_chars), "\n")
            decisions = generate_decisions(llm, transcript, cfg.extraction_max_chars)
            print("DECISIONS\n", json.dumps([d.model_dump() for d in decisions], indent=2), "\n")
            items = generate_action_items(llm, transcript, cfg.extraction_max_chars)
            print("ACTION ITEMS\n", json.dumps([i.model_dump() for i in items], indent=2))
        elif args.command == "delete":
            store.delete_session(args.session)
            print("Deleted.")
    except (TranscriptParseError, LLMError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
