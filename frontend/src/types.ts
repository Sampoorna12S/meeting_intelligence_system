export type Status = "pending" | "processing" | "completed" | "failed";
export type SectionKey = "summary" | "decisions" | "action_items";

export interface Decision {
  decision: string;
  speaker: string | null;
  timestamp: string | null;
}

export interface ActionItem {
  task: string;
  owner: string | null;
  due: string | null;
  timestamp: string | null;
}

export interface StatusResponse {
  session_id: string;
  filename: string;
  indexing: { status: Status; stage: string | null; error: string | null };
  intelligence: Record<SectionKey, Status>;
  errors: Record<SectionKey, string | null>;
  data: { summary: string | null; decisions: Decision[]; action_items: ActionItem[] };
}

export interface Citation {
  id: number;
  speaker: string;
  start: string;
  end: string;
  text: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
}

export interface UploadResponse {
  session_id: string;
  filename: string;
}
