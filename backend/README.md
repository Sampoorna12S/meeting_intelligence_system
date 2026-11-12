# Backend (FastAPI)

Handles uploads, indexing, chat, the status API and the independent meeting intelligence jobs. All AI work is delegated to the [`ai/`](../ai) package. ChromaDB stores both the transcript chunks and the session/status records.

```text
app/
├── main.py                       app factory, CORS, startup recovery
├── config.py                     settings from .env
├── container.py                  wires AI layer + session store + scheduler
├── schemas.py                    request/response models
├── tasks.py                      small thread pool for extraction jobs
├── api/                          upload.py, status.py (+ retry), chat.py, session.py
├── services/
│   ├── processing_service.py     chunk -> embed -> store -> mark completed -> start extraction
│   ├── intelligence_extractor.py three independent section jobs, claim rule, retry
│   └── chat_service.py           checks indexing status, then answers via RAG
└── store/session_store.py        session, status and results in ChromaDB
tests/                            API tests (fake embedder + fake LLM)
```

## Run it locally (Windows / PowerShell)

Requires Python 3.10+. Run everything from the `backend` folder.

```powershell
cd C:\Users\Dell\Sampoorna\Projects\meeting_intelligence_system\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt       # also installs ..\ai in editable mode
copy .env.example .env
```

Edit `.env` and set your LLM provider:

```text
# Groq example
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=your-key
LLM_MODEL=<a model name from the provider's docs>
```

Then start the server:

```powershell
uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/api/health
- Interactive API docs: http://localhost:8000/docs
- On startup the embedding model loads in the background (the first run downloads about 90 MB).

Run the frontend in a second terminal (see [`../frontend/README.md`](../frontend/README.md)).

### Run the tests

```powershell
python -m pytest
```

The tests need no LLM key and no model download.

### Try the API by hand

```powershell
curl.exe -F "file=@..\ai\samples\sample_meeting.txt" http://localhost:8000/api/upload
# -> {"session_id":"session_ab12cd34ef56","filename":"sample_meeting.txt"}
curl.exe http://localhost:8000/api/status/session_ab12cd34ef56
curl.exe -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d "{\"session_id\":\"session_ab12cd34ef56\",\"question\":\"Who updates the pricing page?\"}"
curl.exe -X DELETE http://localhost:8000/api/session/session_ab12cd34ef56
```

## API

| Method | Endpoint | Behaviour |
|---|---|---|
| POST | `/api/upload` | Validate the `.txt`, create a session, index in the background. Returns `202` with `session_id`. |
| GET | `/api/status/{session_id}` | Indexing status/stage, status of each intelligence section, errors, and completed results. |
| POST | `/api/chat` | Answer a question. Needs only indexing to be `completed` (`409` otherwise). Returns `answer` and `citations`. |
| POST | `/api/session/{session_id}/intelligence/{section}/retry` | Re-run a failed `summary`, `decisions` or `action_items` section. |
| DELETE | `/api/session/{session_id}` | Delete the session's chunks and state (also stops in-flight jobs from writing). |
| GET | `/api/health` | Liveness check. |

Error codes: `400` invalid file, `404` unknown session, `409` indexing not complete (or retry of a section that has not failed), `413` file too large, `502` LLM failure.

## Settings (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | empty | OpenAI-compatible LLM. Required for chat and extraction. |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `CHROMA_PATH` | `./data/chroma` | ChromaDB folder (relative to `backend/`) |
| `MAX_UPLOAD_MB` | `2` | Upload size limit |
| `RETRIEVAL_TOP_K` | `5` | Chunks used per question |
| `EXTRACTION_CONCURRENCY` | `2` | How many extraction jobs run at once (keep low on free LLM tiers) |
| `EXTRACTION_MAX_CHARS` | `24000` | Longer transcripts are processed in windows and merged |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |

## Behaviour worth knowing

- **Chat vs extraction:** chat checks indexing status only. The three extraction jobs start after indexing completes and each has its own status (`pending`, `processing`, `completed`, `failed`).
- **No duplicate jobs:** a section moves to `processing` only from `pending` (or from `failed` on retry), under a lock.
- **Restarts:** anything left `pending`/`processing` when the server stopped is marked `failed` on startup, so the UI never shows a loader forever. Sections can be retried; a failed indexing needs a re-upload.
- **Single process:** the locks and job pool are in-process. Run one Uvicorn worker (the default).
- **Reset all data:** stop the server and delete `backend\data\chroma`.

## Troubleshooting

- *Chat or sections fail with "LLM is not configured"*: set `LLM_API_KEY` and `LLM_MODEL` in `.env` and restart.
- *Indexing fails on the first run*: the embedding model could not be downloaded. Check your internet connection and retry the upload.
- *`ModuleNotFoundError: meeting_ai`*: run `pip install -r requirements.txt` from the `backend` folder so `-e ..\ai` resolves.
