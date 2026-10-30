import React, { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react';
import { Citation } from '../types';

interface CitationCardProps {
  citation: Citation;
}

export const CitationCard: React.FC<CitationCardProps> = ({ citation }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="niel-citation-pill">
      <button
        type="button"
        className="niel-citation-btn"
        onClick={() => setExpanded(!expanded)}
        title="View source context"
      >
        <BookOpen size={14} className="niel-citation-icon" />
        <span className="niel-citation-title">{citation.source_filename}</span>
        <span className="niel-citation-badge">Page {citation.page_number}</span>
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {expanded && (
        <div className="niel-citation-content">
          <p className="niel-citation-chunk">
            <strong>Chunk Ref:</strong> <code>{citation.chunk_id}</code>
          </p>
          {citation.quote_snippet && (
            <blockquote className="niel-citation-quote">
              "{citation.quote_snippet}"
            </blockquote>
          )}
        </div>
      )}
    </div>
  );
};

