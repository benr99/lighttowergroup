(function () {
  'use strict';

  // ── Constants ─────────────────────────────────────────────────────────────
  const MAX_TURNS    = 20;    // max user messages per session
  const MAX_CHARS    = 1000;  // max chars per user message
  const WARN_CHARS   = 800;   // show counter when approaching limit

  // ── Styles ────────────────────────────────────────────────────────────────
  const css = `
    #ltg-chat-btn {
      position: fixed; bottom: 1.75rem; right: 1.75rem; z-index: 9000;
      width: 56px; height: 56px; border-radius: 50%;
      background: #c9a84c; border: none; cursor: pointer;
      box-shadow: 0 4px 20px rgba(0,0,0,0.35);
      display: flex; align-items: center; justify-content: center;
      transition: transform 0.2s, background 0.2s;
    }
    #ltg-chat-btn:hover { background: #d9b85c; transform: scale(1.06); }
    #ltg-chat-btn svg { width: 24px; height: 24px; fill: #080c14; }

    #ltg-chat-panel {
      position: fixed; bottom: 5.5rem; right: 1.75rem; z-index: 9000;
      width: 360px; height: 520px;
      background: #0d1826; border: 1px solid rgba(201,168,76,0.3);
      border-radius: 4px; box-shadow: 0 8px 40px rgba(0,0,0,0.5);
      display: flex; flex-direction: column;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      transform: translateY(12px) scale(0.97); opacity: 0;
      pointer-events: none;
      transition: transform 0.22s ease, opacity 0.22s ease;
    }
    #ltg-chat-panel.open {
      transform: translateY(0) scale(1); opacity: 1; pointer-events: all;
    }

    .ltg-chat-header {
      padding: 1rem 1.25rem 0.85rem;
      border-bottom: 1px solid rgba(201,168,76,0.18);
      display: flex; align-items: center; justify-content: space-between;
    }
    .ltg-chat-header-left { display: flex; align-items: center; gap: 0.65rem; }
    .ltg-chat-avatar {
      width: 34px; height: 34px; border-radius: 50%;
      background: #c9a84c; display: flex; align-items: center; justify-content: center;
      font-size: 0.75rem; font-weight: 700; color: #080c14; flex-shrink: 0;
    }
    .ltg-chat-header-name {
      font-size: 0.8rem; font-weight: 600; color: #f4f0e8; letter-spacing: 0.02em;
    }
    .ltg-chat-header-sub {
      font-size: 0.67rem; color: #8a9bb0; margin-top: 1px;
    }
    .ltg-chat-close {
      background: none; border: none; cursor: pointer; color: #8a9bb0;
      font-size: 1.2rem; line-height: 1; padding: 0.2rem;
      transition: color 0.15s;
    }
    .ltg-chat-close:hover { color: #f4f0e8; }

    .ltg-chat-messages {
      flex: 1; overflow-y: auto; padding: 1rem 1.1rem;
      display: flex; flex-direction: column; gap: 0.75rem;
      scrollbar-width: thin; scrollbar-color: rgba(201,168,76,0.2) transparent;
    }

    .ltg-msg {
      max-width: 82%; font-size: 0.84rem; line-height: 1.55;
      padding: 0.65rem 0.9rem; border-radius: 3px; animation: ltgFadeIn 0.2s ease;
    }
    @keyframes ltgFadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

    .ltg-msg-bot {
      background: rgba(255,255,255,0.06); color: rgba(244,240,232,0.88);
      align-self: flex-start; border: 1px solid rgba(255,255,255,0.07);
    }
    .ltg-msg-user {
      background: rgba(201,168,76,0.18); color: #f4f0e8;
      border: 1px solid rgba(201,168,76,0.3); align-self: flex-end;
    }

    .ltg-typing {
      display: flex; gap: 4px; align-items: center;
      padding: 0.65rem 0.9rem; align-self: flex-start;
      background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.07);
      border-radius: 3px;
    }
    .ltg-typing span {
      width: 5px; height: 5px; border-radius: 50%; background: #8a9bb0;
      animation: ltgDot 1.2s infinite;
    }
    .ltg-typing span:nth-child(2) { animation-delay: 0.2s; }
    .ltg-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes ltgDot { 0%,80%,100% { opacity: 0.3; } 40% { opacity: 1; } }

    .ltg-chat-input-row {
      padding: 0.6rem 1rem 0.5rem;
      border-top: 1px solid rgba(201,168,76,0.18);
      display: flex; flex-direction: column; gap: 0.35rem;
    }
    .ltg-input-inner {
      display: flex; gap: 0.5rem; align-items: flex-end;
    }
    .ltg-char-counter {
      font-size: 0.6rem; color: rgba(138,155,176,0.5);
      text-align: right; height: 0.8rem; line-height: 0.8rem;
      opacity: 0; transition: opacity 0.15s;
    }
    .ltg-char-counter.visible { opacity: 1; }
    .ltg-char-counter.warn    { color: #c9a84c; opacity: 1; }
    .ltg-char-counter.over    { color: #e05c5c; opacity: 1; font-weight: 600; }

    .ltg-chat-input {
      flex: 1; background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.12); border-radius: 3px;
      color: #f4f0e8; font-size: 0.84rem; font-family: inherit;
      padding: 0.55rem 0.8rem; resize: none; outline: none;
      transition: border-color 0.15s; line-height: 1.4; max-height: 100px;
    }
    .ltg-chat-input:focus { border-color: rgba(201,168,76,0.5); }
    .ltg-chat-input::placeholder { color: #8a9bb0; }
    .ltg-chat-send {
      width: 36px; height: 36px; border-radius: 3px;
      background: #c9a84c; border: none; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; transition: background 0.15s; align-self: flex-end;
    }
    .ltg-chat-send:hover { background: #d9b85c; }
    .ltg-chat-send:disabled { background: rgba(201,168,76,0.3); cursor: not-allowed; }
    .ltg-chat-send svg { width: 16px; height: 16px; fill: #080c14; }

    .ltg-chat-footer {
      padding: 0.45rem 1rem;
      border-top: 1px solid rgba(255,255,255,0.05);
      text-align: center;
      font-size: 0.62rem; color: rgba(138,155,176,0.6); letter-spacing: 0.05em;
    }

    @media (max-width: 480px) {
      #ltg-chat-panel {
        bottom: 0; right: 0; width: 100vw; height: 100dvh;
        border-radius: 0; border: none;
      }
      #ltg-chat-btn { bottom: 1.25rem; right: 1.25rem; }
    }
  `;

  // ── Inject styles ──────────────────────────────────────────────────────────
  const styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ── Build DOM ─────────────────────────────────────────────────────────────
  document.body.insertAdjacentHTML('beforeend', `
    <button id="ltg-chat-btn" aria-label="Chat with Light Tower Group" title="Talk to us">
      <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"/>
      </svg>
    </button>

    <div id="ltg-chat-panel" role="dialog" aria-label="Light Tower Group Chat" aria-modal="true">
      <div class="ltg-chat-header">
        <div class="ltg-chat-header-left">
          <div class="ltg-chat-avatar">LTG</div>
          <div>
            <div class="ltg-chat-header-name">Light Tower Group</div>
            <div class="ltg-chat-header-sub">Capital Advisory &middot; NYC</div>
          </div>
        </div>
        <button class="ltg-chat-close" id="ltg-chat-close" aria-label="Close chat">&times;</button>
      </div>

      <div class="ltg-chat-messages" id="ltg-chat-messages"></div>

      <div class="ltg-chat-input-row">
        <div class="ltg-input-inner">
          <textarea
            class="ltg-chat-input" id="ltg-chat-input"
            placeholder="Tell us about your deal…"
            rows="1" aria-label="Message input"
            maxlength="1000"
          ></textarea>
          <button class="ltg-chat-send" id="ltg-chat-send" aria-label="Send message">
            <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg>
          </button>
        </div>
        <div class="ltg-char-counter" id="ltg-char-counter" aria-live="polite"></div>
      </div>
      <div class="ltg-chat-footer">Light Tower Group &nbsp;&middot;&nbsp; Capital Advisory</div>
    </div>
  `);

  // ── State ─────────────────────────────────────────────────────────────────
  const messages  = [];   // conversation history for Claude
  let isOpen      = false;
  let isWaiting   = false;
  let userTurns   = 0;    // count of user messages sent

  const panel      = document.getElementById('ltg-chat-panel');
  const btn        = document.getElementById('ltg-chat-btn');
  const closeBtn   = document.getElementById('ltg-chat-close');
  const msgBox     = document.getElementById('ltg-chat-messages');
  const input      = document.getElementById('ltg-chat-input');
  const sendBtn    = document.getElementById('ltg-chat-send');
  const charCount  = document.getElementById('ltg-char-counter');

  // ── Helpers ───────────────────────────────────────────────────────────────
  function togglePanel() {
    isOpen = !isOpen;
    panel.classList.toggle('open', isOpen);
    if (isOpen) {
      input.focus();
      if (messages.length === 0) greet();
    }
  }

  function addMessage(text, role) {
    const el = document.createElement('div');
    el.className = 'ltg-msg ' + (role === 'user' ? 'ltg-msg-user' : 'ltg-msg-bot');
    // textContent is safe — no innerHTML, no XSS risk
    el.textContent = text;
    msgBox.appendChild(el);
    msgBox.scrollTop = msgBox.scrollHeight;
    return el;
  }

  function showTyping() {
    const el = document.createElement('div');
    el.className = 'ltg-typing';
    el.innerHTML = '<span></span><span></span><span></span>';
    el.id = 'ltg-typing';
    msgBox.appendChild(el);
    msgBox.scrollTop = msgBox.scrollHeight;
  }

  function removeTyping() {
    const el = document.getElementById('ltg-typing');
    if (el) el.remove();
  }

  function lockInput(reason) {
    sendBtn.disabled = true;
    input.disabled   = true;
    input.placeholder = reason;
  }

  async function greet() {
    showTyping();
    await delay(700);
    removeTyping();
    addMessage("Hello — what are you working on? Tell me about the deal.", 'bot');
  }

  function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

  // ── Send ──────────────────────────────────────────────────────────────────
  async function sendMessage() {
    const raw  = input.value;
    const text = raw.trim();
    if (!text || isWaiting) return;

    // Hard length check (belt-and-suspenders alongside maxlength attr)
    if (text.length > MAX_CHARS) {
      addMessage(`Please keep messages under ${MAX_CHARS} characters.`, 'bot');
      return;
    }

    // Turn cap — after MAX_TURNS user messages, route to email
    if (userTurns >= MAX_TURNS) {
      addMessage(
        "We've covered a lot — please email ben@lighttowergroup.co to continue this conversation directly.",
        'bot'
      );
      lockInput('Email ben@lighttowergroup.co to continue');
      return;
    }

    input.value = '';
    input.style.height = 'auto';
    updateCharCounter('');
    addMessage(text, 'user');
    messages.push({ role: 'user', content: text });
    userTurns++;

    isWaiting = true;
    sendBtn.disabled = true;
    showTyping();

    try {
      const res = await fetch('/.netlify/functions/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages }),
      });

      const data = await res.json();
      removeTyping();

      if (res.status === 429) {
        addMessage(
          "We've reached the end of what I can help with here — please email ben@lighttowergroup.co directly.",
          'bot'
        );
        lockInput('Email ben@lighttowergroup.co to continue');
        return;
      }

      const reply = data.reply || "I'm having a moment — please email ben@lighttowergroup.co directly.";
      addMessage(reply, 'bot');
      messages.push({ role: 'assistant', content: reply });

    } catch {
      removeTyping();
      addMessage("Network issue — please email ben@lighttowergroup.co directly.", 'bot');
    }

    isWaiting = false;
    sendBtn.disabled = false;
    input.focus();
  }

  // ── Character counter ─────────────────────────────────────────────────────
  function updateCharCounter(value) {
    const len  = value.length;
    const left = MAX_CHARS - len;
    charCount.classList.remove('visible', 'warn', 'over');
    if (len === 0) {
      charCount.textContent = '';
      return;
    }
    charCount.textContent = `${left} remaining`;
    if (left < 0) {
      charCount.classList.add('over');
    } else if (len >= WARN_CHARS) {
      charCount.classList.add('warn');
    } else {
      charCount.classList.add('visible');
    }
  }

  // ── Global API (used by "Initiate Mandate" buttons sitewide) ─────────────
  window.openLTGChat = function() {
    if (!isOpen) togglePanel();
  };

  // ── Event listeners ───────────────────────────────────────────────────────
  btn.addEventListener('click', togglePanel);
  closeBtn.addEventListener('click', togglePanel);
  sendBtn.addEventListener('click', sendMessage);

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize textarea + character counter
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 100) + 'px';
    updateCharCounter(input.value);
  });

})();
