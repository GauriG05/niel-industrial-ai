import React, { useState, useRef, useEffect } from 'react';
import { Send, X, UserCheck, Shield } from 'lucide-react';
import { Message, ChatTurn } from './types';
import { askQuestion } from './services/api';
import { ChatMessage } from './components/ChatMessage';
import { ExamplePrompts } from './components/ExamplePrompts';
import { AdminModal } from './components/AdminModal';
import logoImg from './assets/niel-logo.jpg';
import './App.css';

const getStoredSessionId = (): string => {
  let sid = localStorage.getItem('niel_chat_session_id');
  if (!sid) {
    sid = 'sess_' + Math.random().toString(36).substring(2, 10) + '_' + Date.now();
    localStorage.setItem('niel_chat_session_id', sid);
  }
  return sid;
};

export const App: React.FC = () => {
  const [sessionId] = useState<string>(getStoredSessionId);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(true);
  const [isAdminOpen, setIsAdminOpen] = useState(false);
  const [humanActive, setHumanActive] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  const chatBottomRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Establish persistent WebSocket connection for realtime two-way dialogue
  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${window.location.host}/ws/chat/${sessionId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'session_init') {
          setHumanActive(Boolean(data.human_active));
        } else if (data.type === 'answer') {
          setLoading(false);
          setHumanActive(Boolean(data.human_active));
          const assistantMessage: Message = {
            id: (Date.now() + 1).toString(),
            sender: 'assistant',
            text: data.answer,
            citations: data.citations || [],
            evidence_sufficient: data.evidence_sufficient,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages((prev) => [...prev, assistantMessage]);
        } else if (data.type === 'escalated') {
          setLoading(false);
          setHumanActive(true);
          const alertMessage: Message = {
            id: (Date.now() + 1).toString(),
            sender: 'assistant',
            text: data.answer || 'Your conversation has been routed to a human support engineer.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages((prev) => [...prev, alertMessage]);
        } else if (data.type === 'agent_message') {
          setLoading(false);
          setHumanActive(true);
          const agentMsg: Message = {
            id: (Date.now() + 1).toString(),
            sender: 'agent',
            text: data.content,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages((prev) => [...prev, agentMsg]);
        } else if (data.type === 'session_resolved') {
          setLoading(false);
          setHumanActive(false);
          const resMsg: Message = {
            id: (Date.now() + 1).toString(),
            sender: 'assistant',
            text: data.answer || 'Human support session concluded. The AI assistant is active again.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages((prev) => [...prev, resMsg]);
        } else if (data.type === 'error') {
          setLoading(false);
          const errMsg: Message = {
            id: (Date.now() + 1).toString(),
            sender: 'assistant',
            text: `Error: ${data.detail || data.error || 'Request failed'}`,
            isError: true,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages((prev) => [...prev, errMsg]);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    ws.onerror = () => {
      setWsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [sessionId]);

  const handleEscalate = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setLoading(true);
      wsRef.current.send(JSON.stringify({ action: 'escalate' }));
    }
  };

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

    // If WebSocket is open, send realtime message
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ question: textToSend }));
    } else {
      // Fallback to REST endpoint
      try {
        const priorTurns: ChatTurn[] = messages
          .filter((msg) => !msg.isError && (msg.sender === 'user' || msg.sender === 'assistant'))
          .slice(-8)
          .map((msg) => ({
            role: msg.sender as 'user' | 'assistant',
            content: msg.text,
          }));

        const response = await askQuestion(textToSend, 5, priorTurns, sessionId);
        const isPdfRequested = /\b(pdf|brochure|catalogue|catalog|document|attach|file|download|read source|view source)\b/i.test(textToSend);
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          text: response.answer,
          citations: isPdfRequested ? response.citations : [],
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
    }
  };

  return (
    <div className="niel-viewport-container">
      {/* Pinned Vertical Side Tab matching website's "Enquire Now" tab */}
      <button
        type="button"
        className={`niel-side-tab-launcher ${isOpen ? 'active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="Ask NIEL AI Assistant"
      >
        <span className="niel-side-tab-text">Ask NIEL AI</span>
      </button>

      {/* The Floating Modal Dialog Box matching exact screenshot */}
      {isOpen && (
        <div className="niel-dialog-card">
          {/* Header matching exact mockup */}
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
                <span
                  className={humanActive ? 'niel-amber-dot' : 'niel-green-dot'}
                  title={wsConnected ? 'Realtime Connected' : 'Connecting...'}
                ></span>
                <span className="niel-status-caption">
                  {humanActive ? 'Connected to a human agent' : 'AI Assistant • Product & sales support'}
                </span>
              </div>
            </div>

            {/* Header actions: Escalate button + Admin Dashboard + close X */}
            <div className="niel-header-actions-group">
              {!humanActive && (
                <button
                  type="button"
                  className="niel-escalate-btn"
                  onClick={handleEscalate}
                  disabled={loading}
                  title="Request human support engineer"
                >
                  <UserCheck size={12} />
                  <span>Talk to a human</span>
                </button>
              )}
              <button
                type="button"
                className="niel-action-icon-btn"
                onClick={() => setIsAdminOpen(true)}
                title="Support & Admin Dashboard"
              >
                <Shield size={16} />
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
                placeholder={humanActive ? 'Message human support engineer...' : 'Type your question...'}
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

      {/* Agent & Support Operations Dashboard Modal */}
      <AdminModal isOpen={isAdminOpen} onClose={() => setIsAdminOpen(false)} />
    </div>
  );
};
