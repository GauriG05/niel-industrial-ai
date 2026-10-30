import React, { useState } from 'react';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { Citation } from '../types';

interface CitationCardProps {
  citation: Citation;
}

export const CitationCard: React.FC<CitationCardProps> = ({ citation }) => {
  const [expanded, setExpanded] = useState(false);
  const displayFilename = citation.source_filename.replace(/\.txt$/i, '.pdf');

  return (
    <div className="niel-citation-pill">
      <button
        type="button"
        className="niel-citation-btn"
        onClick={() => setExpanded(!expanded)}
        title="View document source"
      >
        <FileText size={14} className="niel-citation-icon" />
        <span className="niel-citation-title">{displayFilename}</span>
        <span className="niel-citation-badge">Page {citation.page_number}</span>
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {expanded && (
        <div className="niel-citation-content">
          {citation.quote_snippet && (
            <blockquote className="niel-citation-quote">
              "{citation.quote_snippet.replace(/\*\*/g, '')}"
            </blockquote>
          )}
        </div>
      )}
    </div>
  );
};

