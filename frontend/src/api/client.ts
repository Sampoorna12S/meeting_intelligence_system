import type { ChatMessage, ChatResponse, SectionKey, StatusResponse, UploadResponse } from "../types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "Cannot reach the server. Is the backend running?");
  }
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) message = body.detail[0].msg;
    } catch {
      /* keep the default message */
    }
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  upload(file: File): Promise<UploadResponse> {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResponse>("/api/upload", { method: "POST", body: form });
  },
  getStatus(sessionId: string): Promise<StatusResponse> {
    return request<StatusResponse>(`/api/status/${encodeURIComponent(sessionId)}`);
  },
  chat(sessionId: string, question: string, history: ChatMessage[]): Promise<ChatResponse> {
    return request<ChatResponse>("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, question, history }),
    });
  },
  retrySection(sessionId: string, section: SectionKey): Promise<unknown> {
    return request(`/api/session/${encodeURIComponent(sessionId)}/intelligence/${section}/retry`, {
      method: "POST",
    });
  },
  deleteSession(sessionId: string): Promise<void> {
    return request<void>(`/api/session/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
  },
};
