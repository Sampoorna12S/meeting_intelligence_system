# Frontend (React + Vite + TypeScript)

A chat-like UI: upload a transcript, wait for indexing, then ask questions. A side panel shows the meeting summary, key decisions and action items, each loading on its own.

```text
src/
├── App.tsx                       layout, session handling, retry/new-meeting actions
├── types.ts                      API types
├── api/client.ts                 fetch wrapper for the backend
├── hooks/useSessionStatus.ts     polls /api/status every 2s, stops when nothing can change
├── state/processingReducer.ts    indexing + per-section state, isChatEnabled
├── components/
│   ├── UploadPanel.tsx           drag & drop / file picker
│   ├── IndexingProgress.tsx      indexing stages and failure message
│   ├── ChatPanel.tsx             messages, composer (disabled until indexing completes)
│   ├── CitationChip.tsx          speaker + timestamp chip, click to see the excerpt
│   ├── SidePanel.tsx             the three sections
│   └── SectionCard.tsx           loader / error + Retry / content
└── styles.css
```

## Run it locally (Windows / PowerShell)

Requires Node.js 18+ and a running backend (see [`../backend/README.md`](../backend/README.md)) on http://localhost:8000.

```powershell
cd C:\Users\Dell\Sampoorna\Projects\meeting_intelligence_system\frontend
npm install
npm run dev
```

Open http://localhost:5173. In development, Vite proxies `/api` to the backend, so no CORS setup is needed.

Other commands:

```powershell
npm run build      # type-check and build into dist\
npm run preview    # serve the production build locally
```

## Configuration

Normally none. If the backend runs somewhere other than `localhost:8000`, copy `.env.example` to `.env` and set `VITE_API_BASE` (for example `http://localhost:9000`), and add the frontend's origin to `CORS_ORIGINS` in the backend `.env`.

## Behaviour

- **Chat availability** depends only on indexing: `isChatEnabled = indexingStatus === "completed"`. Questions can be asked while the summary, decisions and action items are still generating.
- **Side panel:** each section shows a loader until its own status is `completed`, then its content. A failed section shows its error and a Retry button; the other sections and chat are unaffected.
- **Citations:** answers show chips like `Alice · 00:14:32`. Click a chip to see the transcript excerpt it came from.
- **Refresh:** the current session id is kept in `localStorage`, so reloading the page resumes the session. If the backend no longer knows it, the app returns to the upload screen.
- **New meeting:** deletes the session on the backend and returns to the upload screen.
