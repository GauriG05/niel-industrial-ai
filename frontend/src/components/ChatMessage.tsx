import React, { useState } from 'react';
import { FileText, CheckCircle2 } from 'lucide-react';
import { Message } from '../types';
import { CitationCard } from './CitationCard';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.sender === 'user';
  const [showSources, setShowSources] = useState(false);

  return (
    <div className={`niel-msg-row ${isUser ? 'niel-msg-user' : 'niel-msg-assistant'}`}>
      <div className="niel-msg-bubble-container">
        <div className={`niel-msg-bubble ${message.isError ? 'niel-msg-error' : ''}`}>
          {message.sender === 'agent' && (
            <div className="niel-agent-badge">
              <span>NIEL Support Engineer</span>
            </div>
          )}
          <div className="niel-msg-text">
            {message.text.split('\n').map((line, i) => {
              const cleanLine = line.replace(/\*\*/g, '');
              return (
                <p key={i} style={{ marginBottom: cleanLine ? '6px' : '0' }}>
                  {cleanLine}
                </p>
              );
            })}
          </div>

          {/* Verified Evidence Footer (Discreet, clean, professional) */}
          {!isUser && message.evidence_sufficient === true && (
            <div className="niel-msg-footer-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px', paddingTop: '4px' }}>
              <div className="niel-notice-verified">
                <CheckCircle2 size={13} className="niel-verified-icon" />
                <span>Verified NIEL Specification</span>
              </div>
              {message.citations && message.citations.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowSources(!showSources)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#6b7280',
                    fontSize: '11px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    textDecoration: 'underline'
                  }}
                  title="Click to view reference document"
                >
                  <FileText size={12} />
                  <span>{showSources ? 'Hide PDF' : 'View PDF Source'}</span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Citations/PDFs rendered ONLY when user clicks 'View PDF Source' */}
        {!isUser && showSources && message.citations && message.citations.length > 0 && (
          <div className="niel-citations-section">
            <div className="niel-citations-list">
              {message.citations.map((citation, idx) => (
                <CitationCard key={idx} citation={citation} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
