"""
src/autonomous_agent/widget.py
================================
Streamlit floating draggable chat widget for the Autonomous Agent.

RENDERING ARCHITECTURE (two-layer approach):
  Streamlit's React renderer sanitises HTML injected via st.markdown.  In
  particular, DOMPurify (which Streamlit uses) strips <script> tags and
  inline event handlers (onclick="…").  We work around this with two layers:

  Layer 1 — st.markdown(unsafe_allow_html=True)
    Injects the <style> block and the widget <div> tree.  No JS here.
    DOMPurify allows custom div/button elements with class/id attributes.

  Layer 2 — streamlit.components.v1.html(height=1)
    Renders a minimal <iframe> (height=1px, invisible).  The iframe shares
    the same origin as the parent page, so its JS can reach the parent DOM
    via window.parent.document.  We attach all event listeners here.
    The iframe retries finding the widget elements with setTimeout because
    React may not have committed them to the DOM yet when the script runs.

CHAT HISTORY PERSISTENCE:
  History is stored in window.parent.sessionStorage under key "aa_state_v3".
  sessionStorage survives Streamlit page navigations (same tab) but is cleared
  on browser tab close — intentionally ephemeral (trading session scope).

DRAG IMPLEMENTATION:
  Pure JS mousedown/mousemove/mouseup on the header bar.  No external library
  needed.  Position is stored in state.pos (x, y pixel offsets from the
  default bottom-right anchor) and applied as a CSS transform.

COMMUNICATION:
  The widget sends messages to POST /agent/chat via the Fetch API (not
  XMLHttpRequest — Fetch is cancellable and returns a Promise, cleaner).
  The API base URL is injected from Python as a JS variable (__AA_API).
"""

from __future__ import annotations

import json


# ─────────────────────────────────────────────────────────────────────────────
# CSS — all widget styles in one block
# ─────────────────────────────────────────────────────────────────────────────
# box-sizing: border-box on * ensures padding doesn't overflow containers.
# z-index: 2147483647 is the maximum; guarantees widget appears above Streamlit
# components, tooltips, and modals.
_CSS = """
/* ── Reset for widget subtree ── */
#aa-root *{box-sizing:border-box;margin:0;padding:0;}

/* ── Root anchor — fixed bottom-right, highest stacking context ── */
#aa-root{
  position:fixed;bottom:28px;right:28px;z-index:2147483647;
  font-family:'SF Mono','Cascadia Code',ui-monospace,monospace;font-size:13px;
}

/* ── Chat bubble (collapsed state) ── */
#aa-bubble{
  width:56px;height:56px;border-radius:50%;
  background:linear-gradient(135deg,#58a6ff 0%,#388bfd 100%);
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;font-size:25px;user-select:none;
  box-shadow:0 4px 20px rgba(88,166,255,.45),0 2px 8px rgba(0,0,0,.65);
  transition:transform .15s,box-shadow .15s;
}
#aa-bubble:hover{
  transform:scale(1.09);
  box-shadow:0 6px 28px rgba(88,166,255,.6),0 3px 12px rgba(0,0,0,.75);
}

/* ── Unread badge (green dot on bubble) ── */
#aa-badge{
  position:absolute;top:-2px;right:-2px;width:14px;height:14px;border-radius:50%;
  background:#3fb950;border:2px solid #0d1117;display:none;
}

/* ── Chat window (expanded state) ── */
#aa-window{
  position:absolute;
  bottom:66px;right:0;          /* anchors above the bubble */
  width:390px;height:550px;
  background:#0d1117;           /* GitHub dark background */
  border:1px solid #30363d;border-radius:14px;
  display:flex;flex-direction:column;overflow:hidden;
  box-shadow:0 24px 60px rgba(0,0,0,.85),0 4px 16px rgba(0,0,0,.55);
  opacity:0;                    /* hidden by default */
  transform:translateY(10px) scale(.97);
  pointer-events:none;          /* invisible & non-interactive when closed */
  transition:opacity .2s ease,transform .2s ease;
}
/* .aa-open class is toggled by JS to animate the window in */
#aa-window.aa-open{
  opacity:1;transform:translateY(0) scale(1);pointer-events:all;
}

/* ── Drag handle (header bar) ── */
#aa-header{
  background:#161b22;border-bottom:1px solid #30363d;
  padding:10px 14px;display:flex;align-items:center;gap:8px;
  cursor:grab;user-select:none;flex-shrink:0;
}
#aa-header:active{cursor:grabbing;}

/* ── Title text + green activity dot ── */
#aa-title{
  flex:1;font-weight:600;font-size:12px;letter-spacing:.07em;
  text-transform:uppercase;color:#e6edf3;
  display:flex;align-items:center;gap:6px;
}
.aa-dot{
  width:7px;height:7px;border-radius:50%;
  background:#3fb950;box-shadow:0 0 6px #3fb950;  /* pulsing green = live */
}

/* ── Chat/Agent mode toggle pill ── */
.aa-mode-pill{
  display:flex;background:#0d1117;border:1px solid #30363d;
  border-radius:20px;overflow:hidden;
}
.aa-mode-btn{
  padding:3px 11px;font-size:11px;font-weight:600;letter-spacing:.04em;
  text-transform:uppercase;cursor:pointer;color:#8b949e;
  border:none;background:transparent;
  transition:background .15s,color .15s;
}
/* Blue = Chat mode active */
.aa-mode-btn.active[data-mode="chat"]{background:#58a6ff;color:#fff;border-radius:20px;}
/* Purple = Agent mode active (visual distinction for safety) */
.aa-mode-btn.active[data-mode="agent"]{background:#d2a8ff;color:#0d1117;border-radius:20px;}

/* ── Icon buttons (clear + minimise) ── */
.aa-icon-btn{
  background:none;border:none;color:#8b949e;cursor:pointer;
  font-size:15px;padding:2px 5px;line-height:1;border-radius:4px;
  transition:color .1s,background .1s;
}
.aa-icon-btn:hover{color:#e6edf3;background:#1c2128;}

/* ── Agent-mode warning banner ── */
#aa-warn{
  display:none;
  background:rgba(240,136,62,.12);
  border-bottom:1px solid rgba(240,136,62,.35);
  padding:7px 14px;font-size:11px;color:#f0883e;flex-shrink:0;
}

/* ── Message list ── */
#aa-messages{
  flex:1;overflow-y:auto;padding:12px 14px;
  display:flex;flex-direction:column;gap:10px;
  scrollbar-width:thin;scrollbar-color:#30363d transparent;
}
#aa-messages::-webkit-scrollbar{width:4px;}
#aa-messages::-webkit-scrollbar-thumb{background:#30363d;border-radius:4px;}

/* ── Individual message bubbles ── */
.aa-msg{
  max-width:89%;padding:9px 12px;border-radius:10px;
  line-height:1.5;word-break:break-word;font-size:13px;white-space:pre-wrap;
}
.aa-msg.user{
  align-self:flex-end;
  background:#58a6ff;color:#fff;
  border-bottom-right-radius:3px;   /* "tail" towards send button */
}
.aa-msg.assistant{
  align-self:flex-start;
  background:#1c2128;border:1px solid #30363d;color:#e6edf3;
  border-bottom-left-radius:3px;
}
.aa-msg.assistant code{
  font-family:inherit;background:#161b22;
  padding:1px 5px;border-radius:3px;font-size:12px;color:#58a6ff;
}
.aa-msg.assistant strong{color:#fff;font-weight:600;}
/* System messages (e.g. errors, notices) are centred and de-emphasised */
.aa-msg.system{
  align-self:center;background:transparent;color:#8b949e;
  font-size:11px;font-style:italic;border:none;padding:2px 0;
}

/* ── Typing indicator (three bouncing dots) ── */
.aa-typing{
  align-self:flex-start;
  background:#1c2128;border:1px solid #30363d;
  border-radius:10px;border-bottom-left-radius:3px;
  padding:10px 14px;display:flex;gap:5px;align-items:center;
}
.aa-typing span{
  width:6px;height:6px;border-radius:50%;background:#8b949e;
  animation:aa-bounce 1.2s infinite;
}
.aa-typing span:nth-child(2){animation-delay:.2s;}
.aa-typing span:nth-child(3){animation-delay:.4s;}
@keyframes aa-bounce{
  0%,60%,100%{transform:translateY(0);opacity:.4;}
  30%{transform:translateY(-5px);opacity:1;}
}

/* ── Empty-state placeholder ── */
#aa-empty{
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  height:100%;gap:10px;color:#8b949e;
  font-size:12px;text-align:center;padding:24px;
}
#aa-empty .aa-logo{font-size:40px;margin-bottom:4px;}
#aa-empty p{opacity:.7;line-height:1.6;}

/* ── Suggestion chips (quick-start prompts) ── */
.aa-chip{
  background:#1c2128;border:1px solid #30363d;border-radius:8px;
  padding:7px 12px;cursor:pointer;font-size:11px;color:#8b949e;
  width:100%;text-align:left;
  transition:border-color .15s,color .15s;font-family:inherit;
}
.aa-chip:hover{border-color:#58a6ff;color:#58a6ff;}

/* ── Input row ── */
#aa-input-area{
  padding:10px 12px;border-top:1px solid #30363d;
  display:flex;gap:8px;align-items:flex-end;
  background:#161b22;flex-shrink:0;
}
#aa-input{
  flex:1;background:#0d1117;border:1px solid #30363d;
  border-radius:8px;color:#e6edf3;padding:8px 10px;
  font-family:inherit;font-size:13px;
  resize:none;min-height:36px;max-height:100px;
  outline:none;transition:border-color .15s;line-height:1.4;
}
#aa-input:focus{border-color:#58a6ff;}
#aa-input::placeholder{color:#8b949e;}

/* ── Send button ── */
#aa-send{
  background:#58a6ff;border:none;border-radius:8px;
  color:#fff;width:36px;height:36px;
  cursor:pointer;font-size:18px;
  display:flex;align-items:center;justify-content:center;
  flex-shrink:0;
  transition:background .15s,transform .1s;align-self:flex-end;
}
#aa-send:hover{background:#388bfd;}
#aa-send:active{transform:scale(.92);}
#aa-send:disabled{opacity:.35;cursor:default;transform:none;}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Widget HTML — no onclick attrs; JS attaches listeners after DOMPurify pass
# ─────────────────────────────────────────────────────────────────────────────
_HTML = """\
<div id="aa-root">
  <!-- Collapsed state: circular icon bubble -->
  <div id="aa-bubble" title="Open Trader-Suit AI Agent">
    <span>🤖</span>
    <!-- Green dot appears when there is an unread reply while window is closed -->
    <div id="aa-badge"></div>
  </div>

  <!-- Expanded state: full chat window -->
  <div id="aa-window">
    <!-- Header — also acts as the drag handle -->
    <div id="aa-header">
      <div id="aa-title">
        <!-- Green dot = live connection indicator -->
        <div class="aa-dot"></div>
        Trader-Suit AI
      </div>
      <!-- Mode toggle: Chat (safe) ↔ Agent (can execute) -->
      <div class="aa-mode-pill">
        <button class="aa-mode-btn active" data-mode="chat">Chat</button>
        <button class="aa-mode-btn"        data-mode="agent">Agent</button>
      </div>
      <!-- Clear history -->
      <button class="aa-icon-btn" id="aa-clear-btn" title="Clear chat history">🗑</button>
      <!-- Minimise back to bubble -->
      <button class="aa-icon-btn" id="aa-min-btn"   title="Minimise">─</button>
    </div>

    <!-- Warning banner — only visible in Agent Mode -->
    <div id="aa-warn">
      ⚠ Agent mode can execute real actions — confirm each step before proceeding.
    </div>

    <!-- Message list — grows upward, scrollable -->
    <div id="aa-messages">
      <!-- Empty state: shown until first message is sent -->
      <div id="aa-empty">
        <div class="aa-logo">🤖</div>
        <strong style="color:#e6edf3">Trader-Suit AI Assistant</strong>
        <p>Ask about strategies, positions,<br>price levels, Monte Carlo, or the vault.</p>
        <!-- Quick-start suggestion chips -->
        <button class="aa-chip" id="aa-s1">📊 Show open positions (acct 1)</button>
        <button class="aa-chip" id="aa-s2">⚙️ What is the current workflow state?</button>
        <button class="aa-chip" id="aa-s3">📈 List all production strategies</button>
        <button class="aa-chip" id="aa-s4">🎯 Show US30 price levels</button>
      </div>
    </div>

    <!-- Input row -->
    <div id="aa-input-area">
      <textarea
        id="aa-input"
        placeholder="Ask anything… (Enter to send, Shift+Enter for newline)"
        rows="1"
      ></textarea>
      <button id="aa-send">&#9658;</button>
    </div>
  </div>
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# JavaScript — runs inside the child iframe, wires DOM in window.parent
# ─────────────────────────────────────────────────────────────────────────────
# NOTE: The raw string tag (r"""…""") ensures backslashes are not interpreted
# by Python — important for the regex-like replace patterns inside JS strings.
_JS = r"""
(function() {
  'use strict';

  /* ── Cross-frame references ──────────────────────────────────────────────
     We run inside a sandboxed iframe but need to manipulate DOM elements
     that were injected into the parent page by st.markdown.
     The try/catch gracefully handles edge cases where cross-origin policies
     might block window.parent access (shouldn't happen on localhost/same-tab). */
  var pdoc, pwin, pss;
  try {
    pdoc = window.parent.document;
    pwin = window.parent;
    pss  = window.parent.sessionStorage;    // persist state across page navigations
  } catch(e) {
    pdoc = document;
    pwin = window;
    pss  = sessionStorage;
  }

  /* ── API base URL (injected by Python before this script runs) ── */
  var API_BASE = pwin.__AA_API || 'http://localhost:8000';

  /* ── SessionStorage key — bump version if state schema changes ── */
  var SS_KEY = 'aa_state_v3';

  /* ── Retry loop: React may not have committed the elements yet ───────────
     We check every 200 ms for up to 8 seconds (40 × 200 ms).
     Once found, init() runs exactly once (guarded by dataset.aaInit). */
  function tryInit(n) {
    var root = pdoc.getElementById('aa-root');
    if (!root) {
      if (n > 0) setTimeout(function(){ tryInit(n - 1); }, 200);
      return;
    }
    if (root.dataset.aaInit === '1') return;   // already initialised — idempotent
    root.dataset.aaInit = '1';
    init(root);
  }
  tryInit(40);   // start the retry loop

  /* ═════════════════════════════════════════════════════════════════════════
     INIT — runs once when the widget HTML is confirmed in the parent DOM
     ═════════════════════════════════════════════════════════════════════════ */
  function init(root) {

    /* ── Persistent state object ─────────────────────────────────────────
       Everything the widget needs to remember between page navigations:
         open  : whether the chat window is expanded
         mode  : "chat" | "agent"
         history : array of {role, content} for the current session
         pos   : {x, y} pixel offset from the default anchor position      */
    var state = { open: false, mode: 'chat', history: [], pos: { x: 0, y: 0 } };
    try {
      var saved = pss.getItem(SS_KEY);
      if (saved) Object.assign(state, JSON.parse(saved));
    } catch(_) { /* corrupt storage — start fresh */ }

    /* Save state back to sessionStorage after any mutation */
    function save() {
      try { pss.setItem(SS_KEY, JSON.stringify(state)); } catch(_) {}
    }

    /* ── DOM element references ──────────────────────────────────────────── */
    var winEl   = pdoc.getElementById('aa-window');
    var msgs    = pdoc.getElementById('aa-messages');
    var inp     = pdoc.getElementById('aa-input');
    var sendBtn = pdoc.getElementById('aa-send');
    var emptyEl = pdoc.getElementById('aa-empty');
    var warnEl  = pdoc.getElementById('aa-warn');
    var badge   = pdoc.getElementById('aa-badge');

    /* ── Event wiring ─────────────────────────────────────────────────────
       All listeners are attached here (not in HTML) because DOMPurify strips
       onclick attributes.  Using addEventListener is also best practice:
       multiple listeners can coexist without overwriting each other.        */
    pdoc.getElementById('aa-bubble').addEventListener('click', toggle);
    pdoc.getElementById('aa-clear-btn').addEventListener('click', clearChat);
    pdoc.getElementById('aa-min-btn').addEventListener('click', toggle);

    /* Mode toggle buttons — read data-mode attribute to determine target */
    pdoc.querySelectorAll('.aa-mode-btn').forEach(function(btn) {
      btn.addEventListener('click', function() { setMode(btn.dataset.mode); });
    });

    /* Quick-start suggestion chips */
    pdoc.getElementById('aa-s1').addEventListener('click', function(){ suggest('Show me open positions on account 1'); });
    pdoc.getElementById('aa-s2').addEventListener('click', function(){ suggest('What is the current workflow state?'); });
    pdoc.getElementById('aa-s3').addEventListener('click', function(){ suggest('List all production strategies'); });
    pdoc.getElementById('aa-s4').addEventListener('click', function(){ suggest('What price levels are detected on US30?'); });

    sendBtn.addEventListener('click', send);

    /* Enter = send, Shift+Enter = newline (standard chat UX) */
    inp.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });

    /* Auto-resize textarea as user types multi-line messages */
    inp.addEventListener('input', function() { autoResize(inp); });

    /* ── Drag logic ───────────────────────────────────────────────────────
       We capture mousedown on the header, then track mousemove on the
       document (not just the header) so fast mouse movements don't "lose"
       the drag target.  mouseup releases.                                  */
    var dragging = false, startX, startY, originX, originY;

    pdoc.getElementById('aa-header').addEventListener('mousedown', function(e) {
      if (e.target.tagName === 'BUTTON') return;   // don't drag if clicking a button
      dragging = true;
      startX   = e.clientX;   startY  = e.clientY;
      originX  = state.pos.x; originY = state.pos.y;
      e.preventDefault();     // prevents text selection during drag
    });

    pdoc.addEventListener('mousemove', function(e) {
      if (!dragging) return;
      state.pos.x = originX + (e.clientX - startX);   // delta from mousedown origin
      state.pos.y = originY + (e.clientY - startY);
      applyPos();              // update CSS transform immediately for smooth drag
    });

    pdoc.addEventListener('mouseup', function() {
      if (dragging) { dragging = false; save(); }   // persist final position
    });

    /* ── Apply saved state on page load ─────────────────────────────────── */
    applyMode(state.mode);
    if (state.pos.x || state.pos.y) applyPos();
    if (state.open) openWin();
    renderHistory();   // re-render any messages from this session

    /* ═══════════════════════════════════════════════════════════════════════
       FUNCTIONS
       ═══════════════════════════════════════════════════════════════════════ */

    function toggle() {
      state.open = !state.open;
      save();
      state.open ? openWin() : closeWin();
    }

    function openWin() {
      winEl.classList.add('aa-open');       // triggers CSS transition
      badge.style.display = 'none';         // clear unread indicator
      setTimeout(function() {
        msgs.scrollTop = msgs.scrollHeight; // scroll to latest message
        inp.focus();                        // ready for input immediately
      }, 60);
    }

    function closeWin() {
      winEl.classList.remove('aa-open');    // reverses CSS transition
    }

    function setMode(m) {
      state.mode = m;
      save();
      applyMode(m);
    }

    function applyMode(m) {
      /* Update button active states and warning banner visibility */
      pdoc.querySelectorAll('.aa-mode-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.mode === m);
      });
      warnEl.style.display = (m === 'agent') ? 'block' : 'none';
    }

    function clearChat() {
      state.history = [];
      save();
      msgs.innerHTML = '';      // remove all message bubbles from DOM
      msgs.appendChild(emptyEl);
      emptyEl.style.display = 'flex';   // show the empty-state placeholder again
    }

    /* Pre-fill the input and immediately send — used by suggestion chips */
    function suggest(text) {
      inp.value = text;
      send();
    }

    /* Translate the widget's anchor point by state.pos offset */
    function applyPos() {
      root.style.transform =
        'translate(' + state.pos.x + 'px,' + state.pos.y + 'px)';
    }

    /* ── Send a message ────────────────────────────────────────────────────
       1. Read + clear the input.
       2. Append user bubble to DOM.
       3. Push to history and persist.
       4. Fetch reply from FastAPI.                                          */
    function send() {
      var text = inp.value.trim();
      if (!text) return;          // don't send empty messages
      inp.value = '';
      autoResize(inp);            // reset height after clearing
      addMsg('user', text);
      state.history.push({ role: 'user', content: text });
      save();
      fetchReply(text);
    }

    /* Re-render history after a page navigation (history survives in sessionStorage) */
    function renderHistory() {
      if (!state.history.length) return;
      emptyEl.style.display = 'none';
      state.history.forEach(function(m) { addMsg(m.role, m.content); });
    }

    /* Append a message bubble.  role: "user" | "assistant" | "system" */
    function addMsg(role, text) {
      emptyEl.style.display = 'none';
      var div = pdoc.createElement('div');
      div.className = 'aa-msg ' + role;
      /* Minimal markdown rendering for assistant messages only */
      div.innerHTML = (role === 'assistant') ? formatMd(text) : escHtml(text);
      msgs.appendChild(div);
      msgs.scrollTop = msgs.scrollHeight;   // auto-scroll to new message
    }

    /* Add the three-dot typing animation while waiting for the API */
    function addTyping() {
      var div = pdoc.createElement('div');
      div.className = 'aa-typing';
      div.id = 'aa-typing';
      div.innerHTML = '<span></span><span></span><span></span>';
      msgs.appendChild(div);
      msgs.scrollTop = msgs.scrollHeight;
    }

    /* Remove the typing indicator once the reply arrives */
    function removeTyping() {
      var el = pdoc.getElementById('aa-typing');
      if (el) el.remove();
    }

    /* Escape HTML special chars to prevent XSS in user-supplied text */
    function escHtml(s) {
      return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }

    /* Minimal markdown-to-HTML for assistant responses:
       **bold**, `code`, and newlines.  Full markdown would require a library. */
    function formatMd(text) {
      return escHtml(text)
        .replace(/\*\*(.+?)\*\*/g,   '<strong>$1</strong>')
        .replace(/`([^`]+)`/g,        '<code>$1</code>')
        .replace(/\n/g,               '<br>');
    }

    /* Grow textarea with content, capped at 100px to avoid dominating the view */
    function autoResize(el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 100) + 'px';
    }

    /* ── API call ──────────────────────────────────────────────────────────
       POST /agent/chat with the current message, history (minus the message
       we just added — the API adds it internally), and mode.
       On success: render reply and push to history.
       On error: show a system-level error message in the chat.             */
    function fetchReply(message) {
      sendBtn.disabled = true;
      addTyping();

      /* Exclude the last user message from history — it's the 'message' field */
      var historyPayload = state.history.slice(0, -1);

      fetch(API_BASE + '/agent/chat', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          message: message,
          history: historyPayload,
          mode:    state.mode
        })
      })
      .then(function(res) {
        if (!res.ok) throw new Error('HTTP ' + res.status + ' from /agent/chat');
        return res.json();
      })
      .then(function(data) {
        removeTyping();
        var reply = data.response || '(empty response from agent)';
        addMsg('assistant', reply);
        state.history.push({ role: 'assistant', content: reply });
        save();
        /* Show unread badge if the window is minimised */
        if (!state.open) badge.style.display = 'block';
      })
      .catch(function(err) {
        removeTyping();
        /* Surface the error in-chat with a hint — avoids silent failures */
        addMsg('system',
          '\u26a0 ' + err.message +
          ' — is the FastAPI backend running?  Start with: uvicorn src.api.main:app --reload'
        );
      })
      .finally(function() {
        sendBtn.disabled = false;
        inp.focus();
      });
    }

  } // end init()
})();
"""


# ─────────────────────────────────────────────────────────────────────────────
# Public render function — called from every Streamlit page
# ─────────────────────────────────────────────────────────────────────────────

def render_autonomous_agent_widget(api_base_url: str = "http://localhost:8000") -> None:
    """
    Inject the floating AI chat widget into the current Streamlit page.

    This must be called at the top of every page (after st.set_page_config)
    so the widget appears regardless of which tab the user is on.

    Args:
        api_base_url: Base URL of the FastAPI backend.  Passed to JS so the
                      widget knows where to POST /agent/chat requests.
    """
    import streamlit as st
    import streamlit.components.v1 as components

    # ── Layer 1: inject CSS + HTML structure via st.markdown ──────────────────
    # unsafe_allow_html=True is required to inject custom HTML.
    # DOMPurify (used by Streamlit) will sanitise this but preserve div/button
    # elements and class/id attributes, which is all we need here.
    st.markdown(
        f"<style>{_CSS}</style>{_HTML}",
        unsafe_allow_html=True,
    )

    # ── Layer 2: inject JS via a minimal iframe (height=1) ────────────────────
    # The iframe renders inside the Streamlit DOM tree and has same-origin access
    # to window.parent.document where our widget HTML now lives.
    # We inject __AA_API before the main JS so the script can read it immediately.
    api_json = json.dumps(api_base_url)      # safe JSON encoding (handles localhost ports etc.)
    js_injector = f"""<script>
/* Expose the API base URL to the widget JS before it initialises */
window.parent.__AA_API = {api_json};
{_JS}
</script>"""

    # Collapse the iframe to 0px so it doesn't consume any visual space.
    # We inject the CSS via a second st.markdown call so it applies even if
    # the component renders out-of-order on slow machines.
    st.markdown(
        "<style>"
        "div[data-testid='stCustomComponentV1']{"
        "height:0!important;min-height:0!important;"
        "padding:0!important;margin:0!important;overflow:hidden!important;}"
        "</style>",
        unsafe_allow_html=True,
    )

    # height=1 — the minimum Streamlit allows; the CSS above collapses it to 0
    components.html(js_injector, height=1, scrolling=False)
