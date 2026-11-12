import { useEffect, useRef } from "react";
import type { Dispatch } from "react";
import { api, ApiError } from "../api/client";
import type { ProcessingAction } from "../state/processingReducer";
import type { Status, StatusResponse } from "../types";

const POLL_MS = 2000;

const finished = (s: Status) => s === "completed" || s === "failed";

function isTerminal(p: StatusResponse): boolean {
  if (p.indexing.status === "failed") return true;
  return p.indexing.status === "completed" && Object.values(p.intelligence).every(finished);
}

/**
 * Polls GET /api/status/{id} every 2 seconds and feeds the reducer.
 * Stops once nothing more can change; bump `pollKey` to start again (e.g. after a retry).
 * If the server no longer knows the session (404) `onLost` is called.
 */
export function useSessionStatus(
  sessionId: string | null,
  pollKey: number,
  dispatch: Dispatch<ProcessingAction>,
  onLost: () => void,
): void {
  const onLostRef = useRef(onLost);
  onLostRef.current = onLost;

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      try {
        const payload = await api.getStatus(sessionId);
        if (cancelled) return;
        dispatch({ type: "status_received", payload });
        if (isTerminal(payload)) return;
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          onLostRef.current();
          return;
        }
        // transient error (server restarting, network blip): keep polling
      }
      timer = setTimeout(tick, POLL_MS);
    };

    void tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [sessionId, pollKey, dispatch]);
}
