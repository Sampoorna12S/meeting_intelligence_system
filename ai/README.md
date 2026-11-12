# AI layer (`meeting_ai`)

Everything that touches transcripts, embeddings, ChromaDB and the LLM lives here. The backend only imports from these packages.

```text
meeting_ai/
├── config.py            AIConfig (built from .env by the CLI, from settings by the backend)
├── ingestion/           parser.py (transcript -> turns), chunker.py (speaker-aware chunks)
├── embeddings/          embedder.py (local sentence-transformers)
├── vectorstore/         chroma_client.py (shared client), chunk_store.py (add / query / delete)
├── retrieval/           retriever.py (top-k for one session, returned in meeting order)
├── llm/                 client.py (OpenAI-compatible), json_utils.py (parse JSON + one re-ask)
├── prompts/             rag.py, summary.py, decisions.py, action_items.py
├── rag/                 pipeline.py (retrieve -> context -> LLM), citations.py ([n] -> speaker/time)
├── intelligence/        summary.py, decisions.py, action_items.py, map_reduce.py, models.py
└── cli.py               command line smoke test
```

## Run it locally (Windows / PowerShell)

Requires Python 3.10+.

```powershell
cd C:\Users\Dell\Sampoorna\Projects\meeting_intelligence_system\ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -e ".[dev]"
```

Installing pulls in PyTorch through `sentence-transformers`, which is a large download. The embedding model itself is downloaded on first use.

### 1. Run the tests (no LLM key or model download needed)

```powershell
python -m pytest
```

The tests use a fake embedder and a scripted LLM.

### 2. Try the pipeline from the command line

Create a `.env` file in this folder with your LLM settings (a template is in `..\backend\.env.example`):

```powershell
copy ..\backend\.env.example .env
# edit .env: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
```

Then:

```powershell
python -m meeting_ai.cli index samples\sample_meeting.txt --session demo
python -m meeting_ai.cli ask demo "Who is updating the pricing page?"
python -m meeting_ai.cli extract demo
python -m meeting_ai.cli delete demo
```

`index` needs no LLM key. `ask` and `extract` do. Data is stored in `.\data\chroma` (ignored by git); delete that folder to start fresh.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `LLM_BASE_URL` | empty | Base URL of an OpenAI-compatible API |
| `LLM_API_KEY` | empty | API key |
| `LLM_MODEL` | empty | Model name |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `CHROMA_PATH` | `./data/chroma` | ChromaDB folder |
| `RETRIEVAL_TOP_K` | `5` | Chunks used per question |
| `EXTRACTION_MAX_CHARS` | `24000` | Longer transcripts are processed in windows and merged |

## Notes

- **Transcript formats:** `[00:01:23] Alice: text`, `Alice (00:01:23): text`, `00:01:23 Alice: text` and `Alice: text` (no timestamps). The most common format in the file is used; other lines are appended to the previous turn.
- **Chunking:** adjacent turns by one speaker are merged, chunks target about 800 characters and overlap by one line. Long turns are split on sentence boundaries.
- **Citations:** the model is told to cite excerpt numbers like `[1]`; only markers that map to a real retrieved chunk become citations.
