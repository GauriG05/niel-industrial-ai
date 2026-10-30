import React, { useState, useRef, useEffect } from 'react';
import { Send, RotateCcw, Shield, X } from 'lucide-react';
import { Message } from './types';
import { askQuestion } from './services/api';
import { ChatMessage } from './components/ChatMessage';
import { ExamplePrompts } from './components/ExamplePrompts';
import { AdminModal } from './components/AdminModal';
import './App.css';

// NIEL 3-leaf propeller SVG mark
const NielLogoMark: React.FC = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path
      d="M12 12C12 7.5 15.5 4 19 6C20.5 7.5 20.5 11 16 12M12 12C8 14 4.5 16.5 4 20C4.5 21.5 8 21.5 12 17M12 12C10 7.5 6.5 4.5 3 5C2 6.5 3.5 10 8 12"
      stroke="#f59e0b"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <circle cx="12" cy="12" r="2.5" fill="#f59e0b" />
  </svg>
);

export const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (queryText?: string) => {
    const textToSend = (queryText || input).trim();
    if (!textToSend || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await askQuestion(textToSend);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: response.answer,
        citations: response.citations,
        evidence_sufficient: response.evidence_sufficient,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: `Error: ${err.message || 'Unable to connect to assistant service.'}`,
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setMessages([]);
  };

  return (
    <div className="niel-widget-frame">
      {/* Header matching user image */}
      <header className="niel-widget-header">
        <div className="niel-brand-area">
          <div className="niel-brand-top">
            <NielLogoMark />
            <span className="niel-brand-name">
              <strong>new india</strong> electricals
            </span>
          </div>
          <div className="niel-status-line">
            <span className="niel-status-dot"></span>
            <span className="niel-status-text">Product & sales support</span>
          </div>
        </div>

        <div className="niel-header-tools">
          <button
            type="button"
            className="niel-tool-btn"
            onClick={() => setAdminOpen(true)}
            title="Manage Documents (Admin)"
          >
            <Shield size={16} />
          </button>
          <button
            type="button"
            className="niel-tool-btn"
            onClick={handleReset}
            title="Reset Conversation"
          >
            <RotateCcw size={16} />
          </button>
          <button
            type="button"
            className="niel-tool-btn niel-close-btn"
            onClick={handleReset}
            title="Close"
          >
            <X size={18} />
          </button>
        </div>
      </header>

      {/* Main Conversation Stream */}
      <main className="niel-chat-body">
        {/* Always display the initial welcoming hero card */}
        <div className="niel-greeting-card">
          <p>
            I'm NIEL Assistant. I can help you explore our electrical products,
            understand specifications, and connect you with our team. What can I help you with today?
          </p>
        </div>

        {/* Quick Action Pills right below greeting */}
        <ExamplePrompts onSelectPrompt={(p) => handleSend(p)} disabled={loading} />

        {/* Subsequent User & Assistant Messages */}
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {/* Loading Indicator */}
        {loading && (
          <div className="niel-typing-indicator">
            <span className="niel-dot"></span>
            <span className="niel-dot"></span>
            <span className="niel-dot"></span>
          </div>
        )}

        <div ref={chatBottomRef} />
      </main>

      {/* Input bar matching user image */}
      <form
        className="niel-input-wrapper"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <div className="niel-input-container">
          <input
            type="text"
            className="niel-input-field"
            placeholder="Type your question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={500}
            disabled={loading}
            autoFocus
          />
          <button
            type="submit"
            className="niel-send-btn"
            disabled={!input.trim() || loading}
            aria-label="Send"
          >
            <Send size={16} />
          </button>
        </div>
      </form>

      {/* Admin Document Modal */}
      <AdminModal isOpen={adminOpen} onClose={() => setAdminOpen(false)} />
    </div>
  );
};
