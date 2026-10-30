/**
 * NIEL Industrial Intelligence AI - Embeddable Chat Widget
 * For WordPress 6.x, Elementor, and Standalone Web Pages.
 * 
 * Features:
 * - Shadow DOM encapsulation (Zero CSS clashing with Bootstrap/Elementor/Tailwind).
 * - Standalone Vanilla JS (Zero external dependencies).
 * - Configurable backend URL via window.NIEL_AI_CONFIG.
 * - Mobile responsive floating launcher and chat panel.
 * - Source citation expanders and verified evidence badges.
 */

(function () {
  'use strict';

  // Prevent multiple initializations
  if (window.__NIEL_WIDGET_INITIALIZED__) return;
  window.__NIEL_WIDGET_INITIALIZED__ = true;

  const DEFAULT_CONFIG = {
    apiBase: 'http://127.0.0.1:8000',
    title: 'NIEL Industrial Assistant',
    subtitle: 'Grounded Product AI',
    primaryColor: '#003366',
    accentColor: '#0284c7',
    position: 'bottom-right', // 'bottom-right' or 'bottom-left'
  };

  const config = Object.assign({}, DEFAULT_CONFIG, window.NIEL_AI_CONFIG || {});

  // Create widget host container
  const host = document.createElement('div');
  host.id = 'niel-ai-widget-host';
  document.body.appendChild(host);

  // Attach Shadow DOM for bulletproof CSS isolation
  const shadow = host.attachShadow({ mode: 'open' });

  // Component Styles (Strictly scoped inside Shadow DOM)
  const styles = `
    :host {
      --primary: ${config.primaryColor};
      --primary-dark: #002244;
      --accent: ${config.accentColor};
      --bg: #f8fafc;
      --card: #ffffff;
      --text: #0f172a;
      --text-muted: #64748b;
      --border: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      z-index: 999999;
      position: fixed;
      ${config.position === 'bottom-left' ? 'left: 20px;' : 'right: 20px;'}
      bottom: 20px;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    /* Floating Launcher Button */
    .niel-launcher {
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background: var(--primary);
      color: #ffffff;
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(0, 51, 102, 0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.2s;
    }

    .niel-launcher:hover {
      transform: scale(1.06);
      box-shadow: 0 6px 20px rgba(0, 51, 102, 0.45);
    }

    .niel-launcher svg {
      width: 26px;
      height: 26px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    /* Chat Panel Window */
    .niel-panel {
      position: absolute;
      ${config.position === 'bottom-left' ? 'left: 0;' : 'right: 0;'}
      bottom: 74px;
      width: 380px;
      height: 560px;
      max-width: calc(100vw - 40px);
      max-height: calc(100vh - 100px);
      background: var(--card);
      border-radius: 14px;
      box-shadow: 0 12px 35px rgba(0, 0, 0, 0.18);
      display: none;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid var(--border);
      animation: nielSlideIn 0.25s ease-out;
    }

    .niel-panel.open {
      display: flex;
    }

    @keyframes nielSlideIn {
      from { opacity: 0; transform: translateY(12px) scale(0.97); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    /* Header */
    .niel-header {
      background: var(--primary);
      color: #ffffff;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 2px solid var(--primary-dark);
    }

    .niel-header-title {
      font-weight: 700;
      font-size: 15px;
    }

    .niel-header-subtitle {
      font-size: 11px;
      opacity: 0.85;
    }

    .niel-close-btn {
      background: transparent;
      border: none;
      color: #ffffff;
      cursor: pointer;
      padding: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    /* Messages List */
    .niel-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: var(--bg);
    }

    .niel-msg {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 10px;
      font-size: 13.5px;
      line-height: 1.5;
    }

    .niel-msg-user {
      align-self: flex-end;
      background: var(--primary);
      color: #ffffff;
      border-bottom-right-radius: 2px;
    }

    .niel-msg-assistant {
      align-self: flex-start;
      background: #ffffff;
      color: var(--text);
      border: 1px solid var(--border);
      border-bottom-left-radius: 2px;
    }

    .niel-verified-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      color: #16a34a;
      margin-top: 6px;
      font-weight: 600;
    }

    .niel-unverified-badge {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      color: #b45309;
      background: #fef3c7;
      padding: 4px 8px;
      border-radius: 4px;
      margin-top: 6px;
    }

    .niel-citations {
      margin-top: 8px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .niel-citation-item {
      font-size: 11px;
      background: #f1f5f9;
      padding: 4px 8px;
      border-radius: 4px;
      color: var(--text-muted);
      border-left: 2px solid var(--accent);
    }

    /* Input Footer */
    .niel-footer {
      padding: 12px;
      background: #ffffff;
      border-top: 1px solid var(--border);
      display: flex;
      gap: 8px;
    }

    .niel-input {
      flex: 1;
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 13px;
      outline: none;
      font-family: inherit;
    }

    .niel-input:focus {
      border-color: var(--primary);
    }

    .niel-send {
      background: var(--primary);
      color: #ffffff;
      border: none;
      padding: 0 14px;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .niel-send:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    /* Starter Chips */
    .niel-starters {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-top: 10px;
    }

    .niel-chip {
      background: #ffffff;
      border: 1px solid var(--border);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      cursor: pointer;
      text-align: left;
    }

    .niel-chip:hover {
      border-color: var(--accent);
      color: var(--accent);
    }
  `;

  // Component HTML Structure
  const template = `
    <style>${styles}</style>
    <div class="niel-panel" id="panel">
      <div class="niel-header">
        <div>
          <div class="niel-header-title">${config.title}</div>
          <div class="niel-header-subtitle">${config.subtitle}</div>
        </div>
        <button type="button" class="niel-close-btn" id="closeBtn" aria-label="Close chat">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </div>
      <div class="niel-messages" id="messagesContainer">
        <div class="niel-msg niel-msg-assistant">
          Hello! I am the NIEL Industrial Intelligence Assistant. Ask me about technical specifications, ratings, voltage, or mounting options documented in NIEL product catalogues.
          <div class="niel-starters">
            <button class="niel-chip" data-q="What power ratings are documented for NIEL motors?">⚡ Motor power ratings</button>
            <button class="niel-chip" data-q="What mounting types are listed for these motors?">⚙️ Mounting configurations</button>
            <button class="niel-chip" data-q="What voltage and insulation class is mentioned?">🔌 Voltage & insulation class</button>
          </div>
        </div>
      </div>
      <form class="niel-footer" id="chatForm">
        <input type="text" class="niel-input" id="chatInput" placeholder="Ask about NIEL products..." maxlength="500" required />
        <button type="submit" class="niel-send" id="sendBtn" aria-label="Send">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </form>
    </div>

    <button type="button" class="niel-launcher" id="launcherBtn" aria-label="Open NIEL AI Chat">
      <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
    </button>
  `;

  shadow.innerHTML = template;

  // DOM References
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
        html += `<div class="niel-verified-badge">✓ Grounded in authorized NIEL catalogue</div>`;
      } else if (data.evidence_sufficient === false) {
        html += `<div class="niel-unverified-badge">⚠️ Information not documented in indexed catalogue.</div>`;
      }

      if (data.citations && data.citations.length > 0) {
        html += `<div class="niel-citations">`;
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

  // Delegate click for starter prompt chips
  messagesContainer.addEventListener('click', (e) => {
    const chip = e.target.closest('.niel-chip');
    if (chip && chip.dataset.q) {
      handleSubmit(chip.dataset.q);
    }
  });
})();
