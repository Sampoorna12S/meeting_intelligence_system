import { useCallback, useReducer, useState } from "react";
import { api } from "./api/client";
import ChatPanel from "./components/ChatPanel";
import SidePanel from "./components/SidePanel";
import UploadPanel from "./components/UploadPanel";
import { useSessionStatus } from "./hooks/useSessionStatus";
import { initialState, isChatEnabled, processingReducer } from "./state/processingReducer";
import type { SectionKey } from "./types";

const STORAGE_KEY = "meeting-intelligence-session";

function readStoredSession(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}
function storeSession(id: string | null) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage unavailable: the session just won't survive a refresh */
  }
}

export default function App() {
  const [state, dispatch] = useReducer(processingReducer, undefined, () => initialState(readStoredSession()));
  const [pollKey, setPollKey] = useState(0);

  const clearSession = useCallback(() => {
    storeSession(null);
    dispatch({ type: "reset" });
  }, []);

  useSessionStatus(state.sessionId, pollKey, dispatch, clearSession);

  const onUploaded = (sessionId: string, filename: string) => {
    storeSession(sessionId);
    dispatch({ type: "session_started", sessionId, filename });
    setPollKey((k) => k + 1);
  };

  const newMeeting = async () => {
    const id = state.sessionId;
    clearSession();
    if (id) {
      try {
        await api.deleteSession(id);
      } catch {
        /* already gone or backend unreachable: nothing more to do */
      }
    }
  };

  const retry = async (section: SectionKey) => {
    if (!state.sessionId) return;
    await api.retrySection(state.sessionId, section);
    setPollKey((k) => k + 1); // restart polling so the section flips to "processing"
  };

  return (
    <div className="app">
      <header className="topbar">
        <h1>Meeting Intelligence</h1>
        {state.sessionId && (
          <div className="session-info">
            {state.filename && <span className="file-badge">{state.filename}</span>}
            <button className="btn" onClick={() => void newMeeting()}>
              New meeting
            </button>
          </div>
        )}
      </header>

      {!state.sessionId ? (
        <UploadPanel onUploaded={onUploaded} />
      ) : (
        <main className="layout">
          <ChatPanel
            key={state.sessionId}
            sessionId={state.sessionId}
            enabled={isChatEnabled(state)}
            indexingStatus={state.indexingStatus}
            indexingStage={state.indexingStage}
            indexingError={state.indexingError}
            onReset={() => void newMeeting()}
          />
          <SidePanel state={state} onRetry={retry} />
        </main>
      )}
    </div>
  );
}
