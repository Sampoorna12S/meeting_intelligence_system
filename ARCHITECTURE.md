# Meeting Intelligence System: Architecture

Project folder: `C:\Users\Dell\Sampoorna\Projects\meeting_intelligence_system`

## 1. Goal

A chat-like web UI for meeting transcripts. The user uploads a transcript (`.txt`), and once it has been uploaded and processed (indexed), they can ask questions about the meeting in the chat and get grounded answers with speaker and timestamp citations (RAG). Alongside the chat, a side panel shows an auto-generated summary, key decisions and action items as each one becomes ready.

**Core principle:** indexing is the prerequisite for chat. Meeting intelligence extraction is an independent enhancement that runs alongside chat. Chat never waits on, or fails because of, extraction.

## 2. Tech Stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + Vite + TypeScript, plain CSS |
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic |
| AI layer | Python package `meeting_ai` (parsing, chunking, embeddings, retrieval, LLM calls, prompts) |
| Embeddings | Local `sentence-transformers` (`all-MiniLM-L6-v2`) |
| LLM | OpenAI-compatible client, configured only via `.env` (Groq or Gemini Flash to start) |
| Vector store **and** session store | ChromaDB (persistent, local folder) |
| Background work | FastAPI `BackgroundTasks` plus in-process threads. No Redis or Celery. |

## 3. Workflow

```text
             Upload Transcript
                    |
             Validate + Parse
                    |
         Speaker-aware Chunking
                    |
            Generate Embeddings
                    |
             Store in ChromaDB
                    |
              INDEX READY  ----------------------------+
                    |                                   |
            ENABLE CHAT                       INTELLIGENCE TASKS
                    |                         (3 independent jobs)
             User Question                    Summary | Decisions | Action Items
                    |                                   |
             RAG Retrieval                       each saves its own result
                    |                             and its own status
          Context + LLM (grounded)                      |
                    |                            Side panel updates
        Answer + speaker/time citations           section by section
```

### Stage 1: Indexing (required for chat)

1. Validate upload (`.txt`, UTF-8, size limit, non-empty).
2. Parse into turns: `{speaker, timestamp, text}`.
3. Chunk into speaker-aware chunks.
4. Embed chunks.
5. Store vectors, text and metadata in ChromaDB.
6. Set `indexing.status = completed`. Chat is now enabled.
7. Hand off to Stage 2 without blocking anything.

### Stage 2: Intelligence extraction (independent)

Three separate jobs (`summary`, `decisions`, `action_items`), each with its own status (`pending` → `processing` → `completed` | `failed`) and its own saved result. One failure never blocks the other two or chat.

## 4. Project Structure

```text
meeting_intelligence_system/
├── ARCHITECTURE.md
├── README.md                      # overview + how the three parts fit together
├── .gitignore
├── backend/
│   ├── README.md                  # run steps for the backend
│   ├── requirements.txt           # includes: -e ../ai
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                # FastAPI app, CORS, startup recovery
│   │   ├── config.py              # settings loaded from .env
│   │   ├── container.py           # wires AI layer, session store and scheduler
│   │   ├── api/
│   │   │   ├── upload.py          # POST /api/upload
│   │   │   ├── status.py          # GET /api/status/{id}, retry endpoint
│   │   │   ├── chat.py            # POST /api/chat
│   │   │   ├── session.py         # DELETE /api/session/{id}
│   │   │   └── deps.py            # FastAPI dependency (container)
│   │   ├── services/
│   │   │   ├── processing_service.py     # parse -> chunk -> embed -> index -> trigger extraction
│   │   │   ├── intelligence_extractor.py # runs/persists the 3 section jobs, claims, retries
│   │   │   └── chat_service.py           # indexed-session check + RAG answer
│   │   ├── store/
│   │   │   └── session_store.py   # session + status + results in ChromaDB
│   │   ├── schemas.py             # Pydantic request/response models
│   │   └── tasks.py               # in-process scheduler + per-session locks
│   └── tests/
├── ai/
│   ├── README.md                  # run steps for the AI layer (CLI smoke test)
│   ├── pyproject.toml             # installable package: meeting_ai
│   ├── meeting_ai/
│   │   ├── __init__.py
│   │   ├── config.py              # AIConfig (from .env for the CLI, from backend settings otherwise)
│   │   ├── ingestion/
│   │   │   ├── parser.py          # transcript -> turns {speaker, timestamp, text}
│   │   │   └── chunker.py         # speaker-aware chunking
│   │   ├── embeddings/
│   │   │   └── embedder.py        # sentence-transformers wrapper
│   │   ├── vectorstore/
│   │   │   ├── chroma_client.py   # shared persistent ChromaDB client (also used by backend session store)
│   │   │   └── chunk_store.py     # add / query / delete chunks in `meeting_chunks`
│   │   ├── retrieval/
│   │   │   └── retriever.py       # top-k retrieval filtered by session_id
│   │   ├── llm/
│   │   │   ├── client.py          # OpenAI-compatible client
│   │   │   └── json_utils.py      # parse LLM JSON, one re-ask on invalid output
│   │   ├── prompts/
│   │   │   ├── rag.py             # grounded Q&A prompt
│   │   │   ├── summary.py
│   │   │   ├── decisions.py
│   │   │   └── action_items.py
│   │   ├── rag/
│   │   │   ├── pipeline.py        # retrieve -> build context -> LLM -> answer
│   │   │   └── citations.py       # map [n] markers to chunk metadata
│   │   ├── intelligence/
│   │   │   ├── summary.py         # summary extractor
│   │   │   ├── decisions.py       # decisions extractor
│   │   │   ├── action_items.py    # action items extractor
│   │   │   ├── map_reduce.py      # windowed extraction for long transcripts
│   │   │   └── models.py          # Decision / ActionItem result models
│   │   └── cli.py                 # `python -m meeting_ai.cli index|ask|extract`
│   ├── samples/sample_meeting.txt
│   └── tests/
└── frontend/
    ├── README.md                  # run steps for the frontend
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── api/client.ts
        ├── types.ts
        ├── hooks/useSessionStatus.ts   # polling
        ├── state/processingReducer.ts
        ├── components/
        │   ├── UploadPanel.tsx
        │   ├── IndexingProgress.tsx
        │   ├── ChatPanel.tsx
        │   ├── CitationChip.tsx
        │   ├── SidePanel.tsx
        │   └── SectionCard.tsx         # loader / error+retry / content
        └── App.tsx
```

The AI layer is grouped by responsibility: `ingestion` (parse, chunk), `embeddings`, `vectorstore`, `retrieval`, `llm`, `prompts`, `rag` (chat answers) and `intelligence` (summary, decisions, action items). The backend imports from these packages and never touches the LLM or embedding libraries directly.

Each of `backend/`, `ai/` and `frontend/` gets its own README with step-by-step local setup (Windows/PowerShell commands, `.env` setup, how to run, how to test).

## 5. Data Model (ChromaDB)

Both collections live in the same persistent ChromaDB folder (`backend/data/chroma`).

### Collection `meeting_chunks` (cosine space)

| Field | Value |
|---|---|
| id | `{session_id}:{chunk_index:04d}` |
| document | chunk text, formatted as `[00:01:23] Alice: ...` lines |
| embedding | sentence-transformers vector |
| metadata | `session_id`, `chunk_index`, `speakers` (comma-joined string), `start_seconds`, `end_seconds`, `start_label`, `end_label`, `turn_start`, `turn_end` |

If a transcript has no timestamps, seconds are stored as `-1` and labels as empty, and citations show the speaker only.

### Collection `meeting_sessions` (state, never searched by similarity)

One record per concern, so concurrent jobs never overwrite each other (no read-modify-write races):

| Record id | Holds |
|---|---|
| `{session_id}:meta` | filename, created_at, chunk count |
| `{session_id}:indexing` | status, stage (`parsing`, `chunking`, `embedding`, `storing`), error |
| `{session_id}:summary` | status, error, result |
| `{session_id}:decisions` | status, error, result |
| `{session_id}:action_items` | status, error, result |

Chroma metadata only allows scalar values, so `status`, `kind`, `session_id` and `updated_at` go in metadata. Structured results go in `document` as a JSON string. A constant dummy embedding is supplied, since these records are only fetched by id or `where` filter.

## 6. API

| Method | Endpoint | Behaviour |
|---|---|---|
| POST | `/api/upload` | Validate, create session, start indexing in the background, return `202` with `session_id` |
| GET | `/api/status/{session_id}` | Indexing status/stage, per-section intelligence status, and any completed data |
| POST | `/api/chat` | Answer a question for an indexed session |
| DELETE | `/api/session/{session_id}` | Remove all chunks and state for the session |
| POST | `/api/session/{session_id}/intelligence/{section}/retry` | Re-run one failed section (**added**: the side panel needs it) |

### `POST /api/upload`

`multipart/form-data` with a `file` field. Response `202`: `{ "session_id": "...", "filename": "..." }`.
Errors: `400` wrong type / empty / not UTF-8 / no parseable turns, `413` too large.
The file is parsed synchronously in the request (it is cheap), so a bad file gets a clear `400`; the background task then chunks, embeds and stores.

### `GET /api/status/{session_id}`

```json
{
  "session_id": "session_123",
  "filename": "meeting.txt",
  "indexing": { "status": "completed", "stage": null, "error": null },
  "intelligence": {
    "summary": "completed",
    "decisions": "processing",
    "action_items": "pending"
  },
  "errors": { "summary": null, "decisions": null, "action_items": null },
  "data": {
    "summary": "...",
    "decisions": [],
    "action_items": []
  }
}
```

`404` for an unknown session.

### `POST /api/chat`

Request:

```json
{
  "session_id": "session_123",
  "question": "Who owns the pricing update?",
  "history": [{ "role": "user", "content": "..." }, { "role": "assistant", "content": "..." }]
}
```

`history` is the last few turns (client-managed, max 6 messages), so the backend stays stateless for chat.

Response:

```json
{
  "answer": "Priya will update the pricing page by Friday [1].",
  "citations": [
    { "id": 1, "speaker": "Priya", "start": "00:14:32", "end": "00:14:58", "text": "snippet..." }
  ]
}
```

Errors: `404` unknown session, `409` indexing not completed, `502` LLM failure.
The check is on **indexing status only**, never on intelligence status.

### Result shapes

```text
summary:      string
decisions:    [{ "decision": str, "speaker": str|null, "timestamp": str|null }]
action_items: [{ "task": str, "owner": str|null, "due": str|null, "timestamp": str|null }]
```

LLM output is requested as JSON, validated with Pydantic, and re-asked once if invalid before marking the section `failed`.

## 7. Backend Design

### `processing_service.py`

Runs as a FastAPI background task (sync function, so it runs in the threadpool and doesn't block the event loop during embedding). Updates `indexing` stage as it goes. On success it sets `completed`, then calls the extraction scheduler. On any exception it sets `failed` with an error message.

### `intelligence_extractor.py`

- `start_all(session_id)`: submits three independent section jobs to a small thread pool (concurrency limit configurable, default 2, to respect free-tier LLM rate limits).
- `run_section(session_id, section)`: claims the section, reads the transcript back from ChromaDB ordered by `chunk_index`, calls the AI-layer extractor, saves the result and sets the status.
- **Claim rule:** under a lock, a section moves to `processing` only from `pending` (or from `failed` on retry). Anything else means another task owns it, so the call is a no-op. This prevents duplicate extraction tasks.
- Long transcripts: if the text exceeds a configurable token estimate, use map-reduce (summarise or extract per window, then merge).

### `chat_service.py`

Check session exists and `indexing.status == completed`, embed the question, retrieve top-5 chunks filtered by `session_id`, build context, call the LLM with a grounded prompt, map `[n]` markers to chunk metadata for citations.

### Grounding rules (prompt)

Answer only from the supplied excerpts. If the answer isn't there, say so. Cite with `[n]` markers matching the numbered excerpts.

### Deletion

Delete chunk records and all session state records, and mark the session as deleted in memory so any in-flight job checks this before writing and never recreates state.

### Startup recovery

On startup, any `indexing` or section left in `processing` (from a crash or restart) is set to `failed` with a "interrupted" error, so the UI never shows a loader forever. Sections can then be retried; a failed indexing requires re-upload.

## 8. Frontend Design

### State

```typescript
type Status = "pending" | "processing" | "completed" | "failed";

interface ProcessingState {
  sessionId: string | null;
  indexingStatus: Status;
  indexingStage: string | null;
  intelligence: { summary: Status; decisions: Status; actionItems: Status };
  data: { summary: string | null; decisions: Decision[]; actionItems: ActionItem[] };
}

const isChatEnabled = processingState.indexingStatus === "completed";
```

### Behaviour

- `useSessionStatus` polls `/api/status/{id}` every 2 seconds. It stops when indexing has failed or every section is `completed`/`failed`, and restarts after a retry.
- **Chat area:** disabled with an indexing progress indicator until `indexingStatus === "completed"`, then enabled immediately even while sections are still loading. Answers render with citation chips showing speaker and timestamp.
- **Side panel:** three independent `SectionCard`s (Meeting Summary, Key Decisions, Action Items). Each shows a loader until its own status is `completed`, content when done, and an error message with a Retry button when `failed`.
- The current `session_id` is kept in `localStorage`, so a page refresh resumes the session (state is persisted in ChromaDB).
- A "New meeting" button calls `DELETE /api/session/{id}` and resets the UI.

## 9. Configuration (`backend/.env`)

```text
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHROMA_PATH=./data/chroma
MAX_UPLOAD_MB=2
RETRIEVAL_TOP_K=5
EXTRACTION_CONCURRENCY=2
EXTRACTION_MAX_CHARS=24000
CORS_ORIGINS=http://localhost:5173
```

## 10. Transcript Parsing and Chunking

**Parsing:** supports `[00:01:23] Alice: text` and `Alice (00:01:23): text`. Lines without a speaker prefix are appended to the previous turn. Files with no recognisable turns are rejected with a clear error.

**Chunking:** consecutive turns are grouped (merging adjacent turns by the same speaker) up to a target size of about 800 characters, with one turn of overlap between chunks. A turn is never split unless it alone exceeds the size limit, in which case it is split on sentence boundaries. Each chunk records its speakers and its start/end timestamps for citations.

## 11. Error Handling

| Situation | Behaviour |
|---|---|
| Invalid upload | `400`/`413` with message, no session created |
| Indexing fails | `indexing.status = failed` with error, chat stays disabled, user re-uploads |
| One extraction section fails | Only that section shows error + Retry; chat and other sections unaffected |
| LLM returns invalid JSON | One re-ask, then `failed` |
| LLM unavailable during chat | `502`, chat UI shows error, user can retry the question |
| Server restart mid-processing | Stale `processing` states marked `failed` on startup |

## 12. Implementation Order

1. **AI layer:** parser, chunker, embedder, vector store, retriever, with unit tests and the CLI smoke test, plus `ai/README.md`.
2. **Backend core:** config, session store, upload + status endpoints, indexing background task, `backend/README.md`.
3. **Chat:** RAG answer with citations, the chat endpoint, tests.
4. **Intelligence extraction:** three section jobs, claim rule, retry endpoint, long-transcript map-reduce.
5. **Frontend:** upload and progress, chat with citations, side panel, polling, `frontend/README.md`.
6. **Polish:** root README, end-to-end run against the sample transcript, success-criteria check.

## 13. Success Criteria and How Each Is Verified

| Criterion | Verification |
|---|---|
| Chat available right after ChromaDB indexing | API test: `/api/chat` returns `200` as soon as indexing is `completed`, even with sections `processing` |
| Questions work while extraction runs | Test with a slowed or mocked extractor |
| Side-panel sections load independently | Frontend check: sections flip to content one by one |
| Answers include accurate citations | Test that citation speaker/timestamps match the source chunk metadata |
| Summary/decision failure doesn't affect chat | Test with a forced extractor failure: chat still answers, other sections still complete |
| No duplicate extraction | Test that two simultaneous triggers result in one run |
| Delete cleans everything | Test that chunks and state records are gone after `DELETE` |

## 14. Assumptions (change any of these if needed)

- One transcript per session; a new upload starts a new session.
- Single Uvicorn process (the claim lock and scheduler are in-process).
- Upload limit of 2 MB, retrieval top-5, chat history capped at the last 6 messages sent by the client.
- Status updates by polling, not server-sent events.
- Plain CSS for the frontend (no Tailwind or component library).
- The retry endpoint is an addition to the four endpoints in the workflow doc.
