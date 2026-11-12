import type { Status } from "../types";

const STAGES: [string, string][] = [
  ["chunking", "Splitting the transcript into chunks"],
  ["embedding", "Creating embeddings"],
  ["storing", "Saving to ChromaDB"],
];

interface Props {
  status: Status;
  stage: string | null;
  error: string | null;
  onReset: () => void;
}

export default function IndexingProgress({ status, stage, error, onReset }: Props) {
  if (status === "failed") {
    return (
      <div className="banner banner-error" role="alert">
        <strong>Indexing failed.</strong> {error ?? "Something went wrong while processing the transcript."}
        <div>
          <button className="btn" onClick={onReset}>
            Upload another file
          </button>
        </div>
      </div>
    );
  }
  const current = STAGES.findIndex(([key]) => key === stage);
  return (
    <div className="banner" role="status" aria-live="polite">
      <strong>Preparing your transcript for chat…</strong>
      <ol className="stages">
        {STAGES.map(([key, label], i) => {
          const state = status === "pending" ? "todo" : i < current ? "done" : i === current ? "active" : "todo";
          return (
            <li key={key} className={`stage ${state}`}>
              <span className="dot" />
              {label}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
