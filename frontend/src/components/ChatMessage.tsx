import React from 'react';
import { Bot, User, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Message } from '../types';
import { CitationCard } from './CitationCard';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.sender === 'user';

  return (
    <div className={`niel-msg-row ${isUser ? 'niel-msg-user' : 'niel-msg-assistant'}`}>
      <div className="niel-msg-avatar">
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      <div className="niel-msg-bubble-container">
        <div className={`niel-msg-bubble ${message.isError ? 'niel-msg-error' : ''}`}>
          <div className="niel-msg-header">
            <span className="niel-msg-sender">{isUser ? 'You' : 'NIEL Assistant'}</span>
            <span className="niel-msg-time">{message.timestamp}</span>
          </div>

          <div className="niel-msg-text">
            {message.text.split('\n').map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>

          {/* Insufficient Evidence Warning Notice */}
          {!isUser && message.evidence_sufficient === false && !message.isError && (
            <div className="niel-notice-insufficient">
              <AlertCircle size={14} className="niel-notice-icon" />
              <span>Unverified / Absent in indexed documentation. Commercial or unconfirmed specification.</span>
            </div>
          )}

          {/* Verified Evidence Badge */}
          {!isUser && message.evidence_sufficient === true && (
            <div className="niel-notice-verified">
              <CheckCircle2 size={13} className="niel-verified-icon" />
              <span>Grounded in authorized NIEL technical catalogue</span>
            </div>
          )}
        </div>

        {/* Source Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="niel-citations-section">
            <span className="niel-citations-label">Sources & Citations:</span>
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

