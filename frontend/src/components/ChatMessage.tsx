import React from 'react';
import { Message } from '../types';

interface ChatMessageProps {
  message: Message;
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
                  {cleanLine}
                </p>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
