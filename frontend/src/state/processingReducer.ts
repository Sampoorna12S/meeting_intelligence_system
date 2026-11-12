import type { ActionItem, Decision, Status, StatusResponse } from "../types";

export interface ProcessingState {
  sessionId: string | null;
  filename: string | null;
  indexingStatus: Status;
  indexingStage: string | null;
  indexingError: string | null;
  intelligence: { summary: Status; decisions: Status; actionItems: Status };
  errors: { summary: string | null; decisions: string | null; actionItems: string | null };
  data: { summary: string | null; decisions: Decision[]; actionItems: ActionItem[] };
}

export type ProcessingAction =
  | { type: "session_started"; sessionId: string; filename: string }
  | { type: "status_received"; payload: StatusResponse }
  | { type: "reset" };

export function initialState(sessionId: string | null = null): ProcessingState {
  return {
    sessionId,
    filename: null,
    indexingStatus: "pending",
    indexingStage: null,
    indexingError: null,
    intelligence: { summary: "pending", decisions: "pending", actionItems: "pending" },
    errors: { summary: null, decisions: null, actionItems: null },
    data: { summary: null, decisions: [], actionItems: [] },
  };
}

export function processingReducer(state: ProcessingState, action: ProcessingAction): ProcessingState {
  switch (action.type) {
    case "session_started":
      return { ...initialState(action.sessionId), filename: action.filename };
    case "status_received": {
      const p = action.payload;
      if (p.session_id !== state.sessionId) return state; // stale response from a previous session
      return {
        ...state,
        filename: p.filename || state.filename,
        indexingStatus: p.indexing.status,
        indexingStage: p.indexing.stage,
        indexingError: p.indexing.error,
        intelligence: {
          summary: p.intelligence.summary,
          decisions: p.intelligence.decisions,
          actionItems: p.intelligence.action_items,
        },
        errors: {
          summary: p.errors.summary,
          decisions: p.errors.decisions,
          actionItems: p.errors.action_items,
        },
        data: {
          summary: p.data.summary,
          decisions: p.data.decisions,
          actionItems: p.data.action_items,
        },
      };
    }
    case "reset":
      return initialState(null);
  }
}

/** Chat depends only on indexing, never on intelligence extraction. */
export const isChatEnabled = (s: ProcessingState): boolean => s.indexingStatus === "completed";
