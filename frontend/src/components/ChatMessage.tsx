import React from 'react';
import { Message } from '../types';

interface ChatMessageProps {
  message: Message;
}

const URL_REGEX = /(https?:\/\/[^\s]+)/g;

function renderLineWithLinks(line: string) {
  const parts = line.split(URL_REGEX);

  return parts.map((part, index) => {
    if (part.match(URL_REGEX)) {
      const isWhatsApp = part.includes('wa.me') || part.includes('whatsapp.com');
      if (isWhatsApp) {
        return (
          <span key={index} style={{ display: 'block', margin: '8px 0' }}>
            <a
              href={part}
              target="_blank"
              rel="noopener noreferrer"
              className="niel-wa-btn"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
              </svg>
              <span>Connect on WhatsApp ↗</span>
            </a>
          </span>
        );
      }
      return (
        <a
          key={index}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="niel-msg-link"
        >
          {part}
        </a>
      );
    }
    return part;
  });
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.sender === 'user';

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
                  {renderLineWithLinks(cleanLine)}
                </p>
              );
            })}
          </div>

          {((message.pdf_attachments && message.pdf_attachments.length > 0) || message.site_url) && (
            <div className="niel-attachments-container">
              {message.pdf_attachments?.map((att, idx) => (
                <a
                  key={idx}
                  href={att.url.startsWith('http') ? att.url : `http://127.0.0.1:8000${att.url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="niel-attachment-card niel-pdf-card"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                  </svg>
                  <span className="niel-attachment-title">{att.title || att.filename}</span>
                  <span className="niel-attachment-action">View PDF ↗</span>
                </a>
              ))}
              {message.site_url && (
                <a
                  href={message.site_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="niel-attachment-card niel-site-card"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="2" y1="12" x2="22" y2="12"></line>
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                  </svg>
                  <span className="niel-attachment-title">Product Details</span>
                  <span className="niel-attachment-action">View on website ↗</span>
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
