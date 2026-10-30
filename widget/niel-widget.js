/**
 * NIEL Industrial Intelligence AI - Embeddable Chat Widget
 * Pixel-perfect match for New India Electricals Ltd. website.
 * Features the signature vertical yellow side-tab ("Ask NIEL AI") matching the "Enquire Now" tab.
 */

(function () {
  'use strict';

  if (window.__NIEL_WIDGET_INITIALIZED__) return;
  window.__NIEL_WIDGET_INITIALIZED__ = true;

  const DEFAULT_CONFIG = {
    apiBase: 'http://127.0.0.1:8000',
    tabText: 'Ask NIEL AI',
    brandName: 'new india electricals',
    subTitle: 'Product & sales support',
    brandColor: '#f59e0b',
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
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    /* Vertical Side Tab Launcher matching "Enquire Now" */
    .niel-side-tab {
      position: fixed;
      right: 0;
      top: 48%;
      transform: translateY(-50%);
      background-color: var(--brand-yellow);
      color: #000000;
      border: none;
      border-radius: 6px 0 0 6px;
      padding: 18px 8px;
      cursor: pointer;
      box-shadow: -3px 4px 14px rgba(0, 0, 0, 0.25);
      z-index: 999999;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.15s;
    }

    .niel-side-tab:hover {
      background-color: var(--brand-yellow-hover);
      transform: translateY(-50%) translateX(-2px);
    }

    .niel-side-tab-text {
      writing-mode: vertical-rl;
      transform: rotate(180deg);
      font-size: 13.5px;
      font-weight: 700;
      letter-spacing: 0.8px;
      white-space: nowrap;
      text-transform: uppercase;
    }

    /* Floating Dialog Card */
    .niel-panel {
      position: fixed;
      right: 28px;
      bottom: 28px;
      width: 480px;
      height: 600px;
      max-width: calc(100vw - 36px);
      max-height: calc(100vh - 60px);
      background: #ffffff;
      border-radius: 20px;
      box-shadow: 0 16px 48px rgba(0, 0, 0, 0.26);
      display: none;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid rgba(0, 0, 0, 0.08);
      animation: nielPopIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 999998;
    }

    .niel-panel.open { display: flex; }

    @keyframes nielPopIn {
      from { opacity: 0; transform: translateY(12px) scale(0.97); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* Header */
    .niel-header {
      padding: 18px 22px 14px 22px;
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
      font-size: 1.18rem;
      color: #111827;
      letter-spacing: -0.015em;
    }

    .niel-brand-title strong { font-weight: 700; }

    .niel-status-line {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.78rem;
      color: var(--text-muted);
      margin-top: 2px;
      margin-left: 2px;
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
      border-radius: 4px;
    }
    .niel-close-btn:hover { color: #ef4444; background: #fef2f2; }

    /* Conversation Body */
    .niel-messages {
      flex: 1;
      overflow-y: auto;
      padding: 20px 22px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      background: #ffffff;
    }

    .niel-greeting {
      border: 1px solid var(--border-gray);
      border-radius: 16px;
      padding: 16px 20px;
      font-size: 0.94rem;
      color: #374151;
      line-height: 1.55;
    }

    /* Action Pills */
    .niel-pills-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .niel-pill {
      background: #ffffff;
      border: 1px solid #d1d5db;
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 13px;
      color: #374151;
      cursor: pointer;
      transition: all 0.15s ease;
      white-space: nowrap;
    }

    .niel-pill:hover {
      background: #f9fafb;
      border-color: #9ca3af;
      color: #111827;
      transform: translateY(-1px);
    }

    /* Messages */
    .niel-msg {
      max-width: 88%;
      padding: 12px 18px;
      border-radius: 14px;
      font-size: 13.5px;
      line-height: 1.55;
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
      padding: 14px 22px 20px 22px;
      background: #ffffff;
    }

    .niel-input-box {
      display: flex;
      align-items: center;
      border: 2px solid var(--brand-yellow);
      border-radius: 14px;
      padding: 3px 5px 3px 16px;
      background: #ffffff;
      transition: box-shadow 0.2s;
    }

    .niel-input-box:focus-within {
      box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.25);
    }

    .niel-input {
      flex: 1;
      border: none;
      outline: none;
      font-size: 13.5px;
      font-family: inherit;
      color: #111827;
      background: transparent;
      padding: 8px 0;
    }

    .niel-send-btn {
      width: 38px;
      height: 38px;
      background: var(--brand-yellow);
      color: #000000;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s, transform 0.1s;
    }

    .niel-send-btn:hover {
      background: var(--brand-yellow-hover);
      transform: scale(1.04);
    }
  `;

  const template = `
    <style>${styles}</style>

    <!-- Side-Tab Launcher matching "Enquire Now" -->
    <button type="button" class="niel-side-tab" id="sideTabBtn" aria-label="Open NIEL AI Assistant">
      <span class="niel-side-tab-text">${config.tabText}</span>
    </button>

    <div class="niel-panel" id="panel">
      <div class="niel-header">
        <div>
          <div class="niel-brand-title">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 12C12 7.5 15.5 4 19 6C20.5 7.5 20.5 11 16 12M12 12C8 14 4.5 16.5 4 20C4.5 21.5 8 21.5 12 17M12 12C10 7.5 6.5 4.5 3 5C2 6.5 3.5 10 8 12" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/><circle cx="12" cy="12" r="2.5" fill="#f59e0b"/></svg>
            <span><strong>new india</strong> electricals</span>
          </div>
          <div class="niel-status-line">
            <span class="niel-status-dot"></span>
            <span>${config.subTitle}</span>
          </div>
        </div>
        <button type="button" class="niel-close-btn" id="closeBtn" aria-label="Close">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
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
  `;

  shadow.innerHTML = template;

  const panel = shadow.getElementById('panel');
  const sideTabBtn = shadow.getElementById('sideTabBtn');
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

  sideTabBtn.addEventListener('click', () => togglePanel());
  closeBtn.addEventListener('click', () => togglePanel(false));

  function appendMessage(text, sender, data) {
    const msg = document.createElement('div');
    msg.className = `niel-msg niel-msg-${sender}`;

    const cleanText = text.replace(/\*\*/g, '');
    let html = `<p>${cleanText.replace(/\n/g, '<br/>')}</p>`;

    if (sender === 'assistant' && data) {
      if (data.evidence_sufficient === true) {
        html += `<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
          <span class="niel-verified">✓ Verified NIEL Specification</span>
          ${data.citations && data.citations.length > 0 ? `<button type="button" class="niel-view-pdf-btn" style="background:none;border:none;color:#6b7280;font-size:11px;cursor:pointer;text-decoration:underline;">View PDF Source</button>` : ''}
        </div>`;
      } else if (data.evidence_sufficient === false) {
        html += `<div class="niel-unverified">⚠️ Unverified in indexed catalogue.</div>`;
      }

      if (data.citations && data.citations.length > 0) {
        html += `<div class="niel-citations-drawer" style="display:none; margin-top:6px;">`;
        data.citations.forEach((c) => {
          html += `<div class="niel-citation-item">📄 ${c.source_filename} (Page ${c.page_number})</div>`;
        });
        html += `</div>`;
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
      const isPdfRequested = /\b(pdf|brochure|catalogue|catalog|document|attach|file|download)\b/i.test(text);
      if (!isPdfRequested && data.citations) {
        data.citations = [];
      }
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
      return;
    }

    const pdfBtn = e.target.closest('.niel-view-pdf-btn');
    if (pdfBtn) {
      const msg = pdfBtn.closest('.niel-msg');
      const drawer = msg?.querySelector('.niel-citations-drawer');
      if (drawer) {
        const isHidden = drawer.style.display === 'none';
        drawer.style.display = isHidden ? 'block' : 'none';
        pdfBtn.textContent = isHidden ? 'Hide PDF' : 'View PDF Source';
      }
    }
  });
})();
