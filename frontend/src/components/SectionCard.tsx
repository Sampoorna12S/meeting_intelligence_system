import { useState } from "react";
import type { ReactNode } from "react";
import type { Status } from "../types";

interface Props {
  title: string;
  status: Status;
  error: string | null;
  onRetry: () => Promise<void>;
  children: ReactNode;
}

export default function SectionCard({ title, status, error, onRetry, children }: Props) {
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  const retry = async () => {
    setRetrying(true);
    setRetryError(null);
    try {
      await onRetry();
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : "Retry failed.");
    } finally {
      setRetrying(false);
    }
  };

  return (
    <section className="card">
      <h3>{title}</h3>
      {(status === "pending" || status === "processing") && (
        <div className="loader" role="status" aria-label={`${title} is being generated`}>
          <div className="skeleton w90" />
          <div className="skeleton w75" />
          <div className="skeleton w60" />
          <p className="muted small">{status === "pending" ? "Waiting to start…" : "Generating…"}</p>
        </div>
      )}
      {status === "failed" && (
        <div className="section-error" role="alert">
          <p>{error ?? "This section could not be generated."}</p>
          {retryError && <p className="error-text">{retryError}</p>}
          <button className="btn" onClick={() => void retry()} disabled={retrying}>
            {retrying ? "Retrying…" : "Retry"}
          </button>
        </div>
      )}
      {status === "completed" && children}
    </section>
  );
}
