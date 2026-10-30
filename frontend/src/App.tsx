import React, { useState, useRef, useEffect } from 'react';
import { Send, X, Shield, RotateCcw } from 'lucide-react';
import { Message } from './types';
import { askQuestion } from './services/api';
import { ChatMessage } from './components/ChatMessage';
import { ExamplePrompts } from './components/ExamplePrompts';
import { AdminModal } from './components/AdminModal';
import logoImg from './assets/niel-logo.jpg';
import './App.css';

export const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [isOpen, setIsOpen] = useState(true);
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
    <div className="niel-viewport-container">
      {/* The Floating Modal Dialog Box matching exact screenshot */}
      {isOpen && (
        <div className="niel-dialog-card">
          {/* Header */}
          <div className="niel-dialog-header">
            <div className="niel-header-brand-column">
              <div className="niel-header-logo-row">
                <img
                  src={logoImg}
                  alt="NIEL Logo"
                  className="niel-official-logo"
                />
                <span className="niel-header-text">
                  <span className="niel-text-bold">new india</span>{' '}
                  <span className="niel-text-light">electricals</span>
                </span>
              </div>
              <div className="niel-header-status-row">
                <span className="niel-green-dot"></span>
                <span className="niel-status-caption">Product & sales support</span>
              </div>
            </div>

            <div className="niel-header-actions-group">
              <button
                type="button"
                className="niel-action-icon-btn"
                onClick={() => setAdminOpen(true)}
                title="Manage Technical Documents"
              >
                <Shield size={16} />
              </button>
              <button
                type="button"
                className="niel-action-icon-btn"
                onClick={handleReset}
                title="Reset conversation"
              >
                <RotateCcw size={16} />
              </button>
              <button
                type="button"
                className="niel-action-icon-btn niel-close-x"
                onClick={() => setIsOpen(false)}
                title="Close chat"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          {/* Conversation Stream */}
          <div className="niel-dialog-body">
            {/* Welcoming bubble matching exact screenshot text */}
            <div className="niel-greeting-bubble">
              <p>
                I'm NIEL Assistant. I can help you explore our electrical products,
                understand specifications, and connect you with our team. What can I
                help you with today?
              </p>
            </div>

            {/* Quick Action Pills matching exact screenshot */}
            <ExamplePrompts onSelectPrompt={(p) => handleSend(p)} disabled={loading} />

            {/* Chat History Messages */}
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {/* Typing Indicator */}
            {loading && (
              <div className="niel-typing-bubble">
                <span className="niel-dot"></span>
                <span className="niel-dot"></span>
                <span className="niel-dot"></span>
              </div>
            )}

            <div ref={chatBottomRef} />
          </div>

          {/* Input Box matching yellow border & yellow send button */}
          <form
            className="niel-dialog-footer"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
          >
            <div className="niel-input-gold-container">
              <input
                type="text"
                className="niel-gold-input"
                placeholder="Type your question..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                maxLength={500}
                disabled={loading}
                autoFocus
              />
              <button
                type="submit"
                className="niel-gold-send-btn"
                disabled={!input.trim() || loading}
                aria-label="Send message"
              >
                <Send size={16} color="#000000" />
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Floating Circular Launcher Button visible when closed or peeking */}
      <button
        type="button"
        className="niel-floating-launcher"
        onClick={() => setIsOpen(!isOpen)}
        title="NIEL Assistant"
        aria-label="Toggle NIEL Assistant"
      >
        <img src={logoImg} alt="NIEL" className="niel-launcher-icon" />
      </button>

      {/* Admin Document Management Modal */}
      <AdminModal isOpen={adminOpen} onClose={() => setAdminOpen(false)} />
    </div>
  );
};
