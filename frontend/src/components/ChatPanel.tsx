import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { api } from "../api/client";
import type { ChatMessage, Citation, Status } from "../types";
import CitationChip from "./CitationChip";
import IndexingProgress from "./IndexingProgress";
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface UiMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  isError?: boolean;
}

interface Props {
  sessionId: string;
  enabled: boolean;
  indexingStatus: Status;
  indexingStage: string | null;
  indexingError: string | null;
  onReset: () => void;
}

const SUGGESTIONS = [
  "What were the main decisions?",
  "Who is responsible for which tasks?",
  "What risks were mentioned?",
];

const HISTORY_LIMIT = 6;

export default function ChatPanel({ sessionId, enabled, indexingStatus, indexingStage, indexingError, onReset }: Props) {
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const nextId = useRef(1);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, sending]);

  const ask = async (text: string) => {
    const question = text.trim();
    if (!question || !enabled || sending) return;
    const history: ChatMessage[] = messages
      .filter((m) => !m.isError)
      .slice(-HISTORY_LIMIT)
      .map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { id: nextId.current++, role: "user", content: question }]);
    setInput("");
    setSending(true);
    try {
      const res = await api.chat(sessionId, question, history);
      setMessages((prev) => [
        ...prev,
        { id: nextId.current++, role: "assistant", content: res.answer, citations: res.citations },
      ]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong.";
      setMessages((prev) => [...prev, { id: nextId.current++, role: "assistant", content: msg, isError: true }]);
    } finally {
      setSending(false);
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void ask(input);
    }
  };

  return (
    <section className="chat" aria-label="Chat">
      <div className="messages">
        {!enabled && (
          <IndexingProgress status={indexingStatus} stage={indexingStage} error={indexingError} onReset={onReset} />
        )}
        {enabled && messages.length === 0 && (
          <div className="empty">
            <p>Your transcript is ready. Ask anything about the meeting.</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="btn" onClick={() => void ask(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`msg ${m.role}${m.isError ? " error" : ""}`}>
            <div className="bubble"><Markdown remarkPlugins={[remarkGfm]}>{m.content}</Markdown></div>
            {m.citations && m.citations.length > 0 && (
              <div className="citations">
                {m.citations.map((c) => (
                  <CitationChip key={c.id} citation={c} />
                ))}
              </div>
            )}
          </div>
        ))}
        {sending && (
          <div className="msg assistant">
            <div className="bubble typing" aria-label="Thinking">
              <span /> <span /> <span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="composer">
        <textarea
          value={input}
          rows={1}
          disabled={!enabled}
          placeholder={enabled ? "Ask a question about the meeting…" : "Chat unlocks when indexing finishes…"}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          maxLength={2000}
        />
        <button className="btn primary" disabled={!enabled || sending || !input.trim()} onClick={() => void ask(input)}>
          Send
        </button>
      </div>
    </section>
  );
}
