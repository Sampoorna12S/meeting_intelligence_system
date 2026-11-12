# Meeting Intelligence System

A chat-like web app for meeting transcripts. Upload a `.txt` transcript; once it has been indexed you can ask questions about the meeting and get grounded answers with **speaker and timestamp citations**. Meanwhile a side panel fills in a **summary**, **key decisions** and **action items**, each as soon as it is ready.

> **Core principle:** indexing is the prerequisite for chat. Meeting intelligence extraction is an independent enhancement that runs alongside it. Chat never waits on extraction, and one failed section never affects chat or the other sections.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

## Project layout

| Folder | What it is | Guide |
|---|---|---|
| [`ai/`](ai) | Python package `meeting_ai`: parsing, chunking, embeddings, ChromaDB, retrieval, RAG, extraction | [ai/README.md](ai/README.md) |
| [`backend/`](backend) | FastAPI service: upload, status, chat, session cleanup, background jobs | [backend/README.md](backend/README.md) |
| [`frontend/`](frontend) | React + Vite + TypeScript chat UI with the side panel | [frontend/README.md](frontend/README.md) |

## Quick start (Windows / PowerShell)

Prerequisites: Python 3.10+ and Node.js 18+. You also need an API key for any OpenAI-compatible LLM provider (for example Groq or Google Gemini; both have free tiers).

**1. Backend** (first terminal)

```powershell
cd C:\Users\Dell\Sampoorna\Projects\meeting_intelligence_system\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# edit .env and set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL
uvicorn app.main:app --reload --port 8000
```

**2. Frontend** (second terminal)

```powershell
cd C:\Users\Dell\Sampoorna\Projects\meeting_intelligence_system\frontend
npm install
npm run dev
```

Open http://localhost:5173, upload `ai\samples\sample_meeting.txt` and start asking questions.

The first run downloads the local embedding model (about 90 MB), so the first upload can take a little longer.

## How it works

```text
Upload -> parse -> speaker-aware chunks -> embeddings -> ChromaDB -> INDEX READY
                                                                      |
                                    +---------------------------------+-----------------+
                                    |                                                   |
                              chat enabled                                  3 independent jobs
                          question -> retrieval -> LLM                 summary | decisions | action items
                          answer + citations                           each updates the side panel when done
```

## Running all tests

```powershell
# AI layer
cd ai; pip install -e ".[dev]"; python -m pytest; cd ..
# Backend
cd backend; python -m pytest; cd ..
```
