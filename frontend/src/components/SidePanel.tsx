import type { ProcessingState } from "../state/processingReducer";
import type { SectionKey } from "../types";
import SectionCard from "./SectionCard";

interface Props {
  state: ProcessingState;
  onRetry: (section: SectionKey) => Promise<void>;
}

export default function SidePanel({ state, onRetry }: Props) {
  const { intelligence, errors, data } = state;
  return (
    <aside className="side" aria-label="Meeting intelligence">
      <SectionCard title="Meeting Summary" status={intelligence.summary} error={errors.summary} onRetry={() => onRetry("summary")}>
        <p className="summary">{data.summary}</p>
      </SectionCard>

      <SectionCard title="Key Decisions" status={intelligence.decisions} error={errors.decisions} onRetry={() => onRetry("decisions")}>
        {data.decisions.length === 0 ? (
          <p className="muted">No decisions were identified.</p>
        ) : (
          <ul className="items">
            {data.decisions.map((d, i) => (
              <li key={i}>
                <div>{d.decision}</div>
                {(d.speaker || d.timestamp) && (
                  <div className="meta">
                    {[d.speaker, d.timestamp].filter(Boolean).join(" · ")}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Action Items" status={intelligence.actionItems} error={errors.actionItems} onRetry={() => onRetry("action_items")}>
        {data.actionItems.length === 0 ? (
          <p className="muted">No action items were identified.</p>
        ) : (
          <ul className="items">
            {data.actionItems.map((a, i) => (
              <li key={i}>
                <div>{a.task}</div>
                <div className="meta">
                  <span className="tag">{a.owner ?? "Unassigned"}</span>
                  {a.due && <span className="tag due">Due: {a.due}</span>}
                  {a.timestamp && <span>{a.timestamp}</span>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </aside>
  );
}
