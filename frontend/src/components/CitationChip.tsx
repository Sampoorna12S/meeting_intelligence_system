import { useState } from "react";
import type { Citation } from "../types";

export default function CitationChip({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false);
  const time = citation.start ? (citation.end && citation.end !== citation.start ? `${citation.start}–${citation.end}` : citation.start) : "";
  return (
    <div className="citation">
      <button className="chip" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="chip-id">{citation.id}</span>
        {citation.speaker}
        {time && <span className="chip-time"> · {time}</span>}
      </button>
      {open && <blockquote className="snippet">{citation.text}</blockquote>}
    </div>
  );
}
