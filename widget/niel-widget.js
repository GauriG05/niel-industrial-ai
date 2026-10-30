/**
 * NIEL Industrial Intelligence AI - Embeddable Chat Widget
 * Pixel-perfect match for New India Electricals Ltd. brand identity.
 */

(function () {
  'use strict';

  if (window.__NIEL_WIDGET_INITIALIZED__) return;
  window.__NIEL_WIDGET_INITIALIZED__ = true;

  const DEFAULT_CONFIG = {
    apiBase: 'http://127.0.0.1:8000',
    brandName: 'new india electricals',
    subTitle: 'Product & sales support',
    brandColor: '#f59e0b',
    position: 'bottom-right',
  };

  const config = Object.assign({}, DEFAULT_CONFIG, window.NIEL_AI_CONFIG || {});

  const host = document.createElement('div');
  host.id = 'niel-ai-widget-host';
  document.body.appendChild(host);

  const shadow = host.attachShadow({ mode: 'open' });

  const styles = `
    :host {
      --brand-yellow: ${config.brandColor};
      --brand-yellow-hover: #d97706;
      --status-green: #22c55e;
      --border-gray: #e5e7eb;
      --text-dark: #1f2937;
      --text-muted: #6b7280;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      z-index: 999999;
      position: fixed;
      ${config.position === 'bottom-left' ? 'left: 24px;' : 'right: 24px;'}
      bottom: 24px;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    /* Launcher Button (Yellow brand icon) */
    .niel-launcher {
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background: #ffffff;
      border: 2px solid var(--brand-yellow);
      cursor: pointer;
      box-shadow: 0 4px 18px rgba(0, 0, 0, 0.15);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    .niel-launcher:hover {
      transform: scale(1.08);
    }

    .niel-launcher svg {
      width: 30px;
      height: 30px;
    }

    /* Floating Panel */
    .niel-panel {
      position: absolute;
      ${config.position === 'bottom-left' ? 'left: 0;' : 'right: 0;'}
      bottom: 72px;
      width: 440px;
      height: 580px;
      max-width: calc(100vw - 36px);
      max-height: calc(100vh - 90px);
      background: #ffffff;
      border-radius: 20px;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.16);
      display: none;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid rgba(0, 0, 0, 0.08);
      animation: nielSlideIn 0.22s ease-out;
    }

    .niel-panel.open { display: flex; }

    @keyframes nielSlideIn {
      from { opacity: 0; transform: translateY(12px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* Header */
    .niel-header {
      padding: 16px 20px 12px 20px;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      border-bottom: 1px solid #f3f4f6;
      background: #ffffff;
    }

    .niel-brand-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 1.15rem;
      color: #111827;
      letter-spacing: -0.01em;
    }

    .niel-brand-title strong { font-weight: 700; }

    .niel-status-line {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.78rem;
      color: var(--text-muted);
      margin-top: 2px;
    }

    .niel-status-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--status-green);
      display: inline-block;
    }

    .niel-close-btn {
      background: none;
      border: none;
      color: #9ca3af;
      cursor: pointer;
      padding: 4px;
      display: flex;
    }
    .niel-close-btn:hover { color: #ef4444; }

    /* Conversation Body */
    .niel-messages {
      flex: 1;
      overflow-y: auto;
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #ffffff;
    }

    .niel-greeting {
      border: 1px solid var(--border-gray);
      border-radius: 14px;
      padding: 14px 18px;
      font-size: 13.5px;
      color: #374151;
      line-height: 1.5;
    }

    /* Action Pills */
    .niel-pills-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 2px 0 6px 0;
    }

    .niel-pill {
      background: #ffffff;
      border: 1px solid #d1d5db;
      padding: 6px 12px;
      border-radius: 9999px;
      font-size: 12px;
      color: #374151;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .niel-pill:hover {
      background: #f9fafb;
      border-color: #9ca3af;
      color: #111827;
    }

    /* Messages */
    .niel-msg {
      max-width: 88%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 13px;
      line-height: 1.5;
    }

    .niel-msg-user {
      align-self: flex-end;
      background: #1f2937;
      color: #ffffff;
      border-bottom-right-radius: 2px;
    }

    .niel-msg-assistant {
      align-self: flex-start;
      background: #ffffff;
      color: #1f2937;
      border: 1px solid var(--border-gray);
      border-bottom-left-radius: 2px;
    }

    .niel-verified {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      color: #15803d;
      margin-top: 6px;
      font-weight: 500;
    }

    .niel-unverified {
      font-size: 11px;
      color: #b45309;
      background: #fef3c7;
      padding: 4px 8px;
      border-radius: 4px;
      margin-top: 6px;
    }

    .niel-citation-item {
      font-size: 11px;
      background: #f9fafb;
      padding: 4px 8px;
      border-radius: 4px;
      color: var(--text-muted);
      border-left: 2px solid var(--brand-yellow);
      margin-top: 4px;
    }

    /* Input Bar with Yellow outline & yellow send button */
    .niel-footer {
      padding: 14px 20px 18px 20px;
      background: #ffffff;
    }

    .niel-input-box {
      display: flex;
      align-items: center;
      border: 2px solid var(--brand-yellow);
      border-radius: 12px;
      padding: 3px 5px 3px 14px;
      background: #ffffff;
    }

    .niel-input {
      flex: 1;
      border: none;
      outline: none;
      font-size: 13.5px;
      font-family: inherit;
      color: #111827;
      background: transparent;
    }

    .niel-send-btn {
      width: 34px;
      height: 34px;
      background: var(--brand-yellow);
      color: #000000;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .niel-send-btn:hover { background: var(--brand-yellow-hover); }
  `;

  const template = `
    <style>${styles}</style>
    <div class="niel-panel" id="panel">
      <div class="niel-header">
        <div>
          <div class="niel-brand-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 12C12 7.5 15.5 4 19 6C20.5 7.5 20.5 11 16 12M12 12C8 14 4.5 16.5 4 20C4.5 21.5 8 21.5 12 17M12 12C10 7.5 6.5 4.5 3 5C2 6.5 3.5 10 8 12" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/><circle cx="12" cy="12" r="2.5" fill="#f59e0b"/></svg>
            <span><strong>new india</strong> electricals</span>
          </div>
          <div class="niel-status-line">
            <span class="niel-status-dot"></span>
            <span>${config.subTitle}</span>
          </div>
        </div>
        <button type="button" class="niel-close-btn" id="closeBtn" aria-label="Close">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </div>

      <div class="niel-messages" id="messagesContainer">
        <div class="niel-greeting">
          I'm NIEL Assistant. I can help you explore our electrical products, understand specifications, and connect you with our team. What can I help you with today?
        </div>

        <div class="niel-pills-row">
          <button class="niel-pill" data-q="What does NIEL make?">What does NIEL make?</button>
          <button class="niel-pill" data-q="Transformer details">Transformer details</button>
          <button class="niel-pill" data-q="Switchgear & panels">Switchgear & panels</button>
          <button class="niel-pill" data-q="Industries served">Industries served</button>
        </div>

        <div class="niel-pills-row">
          <button class="niel-pill" data-q="What do you need for a quote?">What do you need for a quote?</button>
          <button class="niel-pill" data-q="Request a quote">Request a quote</button>
          <button class="niel-pill" data-q="Talk to sales">Talk to sales</button>
        </div>
      </div>

      <form class="niel-footer" id="chatForm">
        <div class="niel-input-box">
          <input type="text" class="niel-input" id="chatInput" placeholder="Type your question..." maxlength="500" required />
          <button type="submit" class="niel-send-btn" id="sendBtn" aria-label="Send">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          </button>
        </div>
      </form>
    </div>

    <button type="button" class="niel-launcher" id="launcherBtn" aria-label="Open NIEL Assistant">
      <svg viewBox="0 0 24 24" fill="none"><path d="M12 12C12 7.5 15.5 4 19 6C20.5 7.5 20.5 11 16 12M12 12C8 14 4.5 16.5 4 20C4.5 21.5 8 21.5 12 17M12 12C10 7.5 6.5 4.5 3 5C2 6.5 3.5 10 8 12" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/><circle cx="12" cy="12" r="2.5" fill="#f59e0b"/></svg>
    </button>
  `;

  shadow.innerHTML = template;

  const panel = shadow.getElementById('panel');
  const launcherBtn = shadow.getElementById('launcherBtn');
  const closeBtn = shadow.getElementById('closeBtn');
  const chatForm = shadow.getElementById('chatForm');
  const chatInput = shadow.getElementById('chatInput');
  const sendBtn = shadow.getElementById('sendBtn');
  const messagesContainer = shadow.getElementById('messagesContainer');

  let isOpen = false;

  function togglePanel(open) {
    isOpen = typeof open === 'boolean' ? open : !isOpen;
    if (isOpen) {
      panel.classList.add('open');
      chatInput.focus();
    } else {
      panel.classList.remove('open');
    }
  }

  launcherBtn.addEventListener('click', () => togglePanel());
  closeBtn.addEventListener('click', () => togglePanel(false));

  function appendMessage(text, sender, data) {
    const msg = document.createElement('div');
    msg.className = `niel-msg niel-msg-${sender}`;

    let html = `<p>${text.replace(/\\n/g, '<br/>')}</p>`;

    if (sender === 'assistant' && data) {
      if (data.evidence_sufficient === true) {
        html += `<div class="niel-verified">✓ Grounded in authorized NIEL catalogue</div>`;
      } else if (data.evidence_sufficient === false) {
        html += `<div class="niel-unverified">⚠️ Unverified in indexed catalogue.</div>`;
      }

      if (data.citations && data.citations.length > 0) {
        data.citations.forEach((c) => {
          html += `<div class="niel-citation-item">📄 ${c.source_filename} (Page ${c.page_number})</div>`;
        });
      }
    }

    msg.innerHTML = html;
    messagesContainer.appendChild(msg);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  async function handleSubmit(query) {
    const text = (query || chatInput.value).trim();
    if (!text) return;

    appendMessage(text, 'user');
    chatInput.value = '';
    sendBtn.disabled = true;

    try {
      const res = await fetch(`${config.apiBase}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text, top_k: 5 }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Service request failed');
      }

      const data = await res.json();
      appendMessage(data.answer, 'assistant', data);
    } catch (err) {
      appendMessage(`Error: ${err.message || 'Unable to connect to assistant.'}`, 'assistant', { evidence_sufficient: false });
    } finally {
      sendBtn.disabled = false;
    }
  }

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    handleSubmit();
  });

  messagesContainer.addEventListener('click', (e) => {
    const pill = e.target.closest('.niel-pill');
    if (pill && pill.dataset.q) {
      handleSubmit(pill.dataset.q);
    }
  });
})();
