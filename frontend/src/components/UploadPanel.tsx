import { useRef, useState } from "react";
import type { DragEvent } from "react";
import { api } from "../api/client";

interface Props {
  onUploaded: (sessionId: string, filename: string) => void;
}

export default function UploadPanel({ onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = async (file: File | undefined) => {
    if (!file || busy) return;
    setError(null);
    if (!file.name.toLowerCase().endsWith(".txt")) {
      setError("Please choose a .txt transcript file.");
      return;
    }
    setBusy(true);
    try {
      const res = await api.upload(file);
      onUploaded(res.session_id, res.filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    void send(e.dataTransfer.files[0]);
  };

  return (
    <div className="upload-wrap">
      <div
        className={`dropzone${dragging ? " dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <h2>Upload a meeting transcript</h2>
        <p className="muted">
          Drop a <code>.txt</code> file here, then chat with it and get a summary, key decisions and action items.
        </p>
        <button className="btn primary" disabled={busy} onClick={() => inputRef.current?.click()}>
          {busy ? "Uploading…" : "Choose file"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".txt,text/plain"
          hidden
          onChange={(e) => void send(e.target.files?.[0])}
        />
        <p className="hint">
          Lines like <code>[00:01:23] Alice: text</code>, <code>Alice (00:01:23): text</code> or <code>Alice: text</code>
        </p>
        {error && (
          <p className="error-text" role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
