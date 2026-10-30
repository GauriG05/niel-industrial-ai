import React, { useState, useRef, useEffect } from 'react';
import { Send, RotateCcw, Shield, Cpu, Sparkles } from 'lucide-react';
import { Message } from './types';
import { askQuestion } from './services/api';
import { ChatMessage } from './components/ChatMessage';
import { ExamplePrompts } from './components/ExamplePrompts';
import { AdminModal } from './components/AdminModal';
import './App.css';

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
        text: `Error: ${err.message || 'Unable to connect to the assistant service.'}`,
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    if (messages.length === 0) return;
    if (confirm('Reset conversation history?')) {
      setMessages([]);
    }
  };

  return (
    <div className="niel-app-layout">
      {/* Header */}
      <header className="niel-header">
        <div className="niel-header-brand">
          <div className="niel-header-icon">
            <Cpu size={22} />
          </div>
          <div>
            <h1 className="niel-header-title">NIEL Industrial Intelligence AI</h1>
            <p className="niel-header-subtitle">New India Electricals Ltd. • Grounded Product Assistant</p>
          </div>
        </div>

        <div className="niel-header-actions">
          <button
            type="button"
            className="niel-icon-btn"
            onClick={handleReset}
            title="Reset conversation"
            disabled={messages.length === 0}
          >
            <RotateCcw size={14} />
            <span>Reset</span>
          </button>
          <button
            type="button"
            className="niel-icon-btn"
            onClick={() => setAdminOpen(true)}
            title="Document Management"
          >
            <Shield size={14} />
            <span>Documents</span>
          </button>
        </div>
      </header>

      {/* Chat Viewport */}
      <main className="niel-chat-viewport">
        {messages.length === 0 ? (
          <div className="niel-empty-state">
            <div className="niel-empty-badge">
              <Sparkles size={12} />
              <span>Grounded Knowledge Base</span>
            </div>
            <h2>Industrial Electrical Specifications</h2>
            <p>
              Ask questions about power ratings, voltage, insulation classes, mounting configurations,
              and cooling methods directly sourced from authorized NIEL product documentation.
            </p>
            <ExamplePrompts onSelectPrompt={(p) => handleSend(p)} disabled={loading} />
          </div>
        ) : (
          messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
        )}

        {/* Loading state indicator */}
        {loading && (
          <div className="niel-msg-row niel-msg-assistant">
            <div className="niel-msg-avatar">
              <Cpu size={18} />
            </div>
            <div className="niel-msg-bubble">
              <div className="niel-loading-dots">
                <span className="niel-dot"></span>
                <span className="niel-dot"></span>
                <span className="niel-dot"></span>
              </div>
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </main>

      {/* Input bar */}
      <form
        className="niel-input-form"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <input
          type="text"
          className="niel-input-field"
          placeholder="Ask about NIEL motor ratings, mounting, voltage, or pump specs..."
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
          title="Send query"
        >
          <Send size={16} />
          <span>Send</span>
        </button>
      </form>

      {/* Admin Modal */}
      <AdminModal isOpen={adminOpen} onClose={() => setAdminOpen(false)} />
    </div>
  );
};

