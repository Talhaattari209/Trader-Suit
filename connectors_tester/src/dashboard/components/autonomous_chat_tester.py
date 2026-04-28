"""
connectors_tester/src/dashboard/components/autonomous_chat_tester.py
======================================================================
Floating draggable chat widget for the Connectors Tester.

Adapted from the main project's src/autonomous_agent/widget.py with these changes:
  1. POST endpoint is /ct/agent/chat (tester-specific route, not /agent/chat).
  2. The broker is passed as a JS variable so the widget sends it with every request.
  3. The suggestion chips are broker-specific (injected by Python, not hardcoded).
  4. The orange accent colour distinguishes it visually from the main project widget.

Architecture (two-layer — same rationale as main widget):
  Layer 1: st.markdown → CSS + HTML structure (DOMPurify-safe, no scripts)
  Layer 2: components.v1.html (height=1 iframe) → JS wires all events
"""

from __future__ import annotations

import json


_CSS = """
/* ── Reset ── */
#ct-root *{box-sizing:border-box;margin:0;padding:0;}

/* ── Root anchor — always on top ── */
#ct-root{
  position:fixed;bottom:28px;right:28px;z-index:2147483647;
  font-family:'SF Mono','Cascadia Code',ui-monospace,monospace;font-size:13px;
}

/* ── Bubble — orange to distinguish from main project (blue) ── */
#ct-bubble{
  width:56px;height:56px;border-radius:50%;
  background:linear-gradient(135deg,#f0883e 0%,#d97706 100%);
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;font-size:25px;user-select:none;
  box-shadow:0 4px 20px rgba(240,136,62,.45),0 2px 8px rgba(0,0,0,.65);
  transition:transform .15s,box-shadow .15s;
}
#ct-bubble:hover{transform:scale(1.09);box-shadow:0 6px 28px rgba(240,136,62,.6);}

/* ── Unread badge ── */
#ct-badge{
  position:absolute;top:-2px;right:-2px;width:14px;height:14px;border-radius:50%;
  background:#3fb950;border:2px solid #0d1117;display:none;
}

/* ── Chat window ── */
#ct-window{
  position:absolute;bottom:66px;right:0;width:395px;height:560px;
  background:#0d1117;border:1px solid #30363d;border-radius:14px;
  display:flex;flex-direction:column;overflow:hidden;
  box-shadow:0 24px 60px rgba(0,0,0,.85),0 4px 16px rgba(0,0,0,.55);
  opacity:0;transform:translateY(10px) scale(.97);pointer-events:none;
  transition:opacity .2s ease,transform .2s ease;
}
#ct-window.ct-open{opacity:1;transform:translateY(0) scale(1);pointer-events:all;}

/* ── Header / drag handle ── */
#ct-header{
  background:#161b22;border-bottom:1px solid #30363d;
  padding:10px 14px;display:flex;align-items:center;gap:8px;
  cursor:grab;user-select:none;flex-shrink:0;
}
#ct-header:active{cursor:grabbing;}

/* ── Title ── */
#ct-title{
  flex:1;font-weight:600;font-size:12px;letter-spacing:.07em;
  text-transform:uppercase;color:#e6edf3;
  display:flex;align-items:center;gap:6px;
}
.ct-dot{width:7px;height:7px;border-radius:50%;background:#f0883e;box-shadow:0 0 6px #f0883e;}

/* ── Broker badge (shows current broker next to title) ── */
#ct-broker-badge{
  background:#1c2128;border:1px solid #f0883e;border-radius:8px;
  padding:2px 8px;font-size:10px;color:#f0883e;font-weight:600;letter-spacing:.04em;
}

/* ── Mode toggle ── */
.ct-mode-pill{display:flex;background:#0d1117;border:1px solid #30363d;border-radius:20px;overflow:hidden;}
.ct-mode-btn{
  padding:3px 11px;font-size:11px;font-weight:600;letter-spacing:.04em;
  text-transform:uppercase;cursor:pointer;color:#8b949e;
  border:none;background:transparent;transition:background .15s,color .15s;
}
/* Orange = Chat active */
.ct-mode-btn.active[data-mode="chat"]{background:#f0883e;color:#fff;border-radius:20px;}
/* Purple = Agent active */
.ct-mode-btn.active[data-mode="agent"]{background:#d2a8ff;color:#0d1117;border-radius:20px;}

/* ── Icon buttons ── */
.ct-icon-btn{
  background:none;border:none;color:#8b949e;cursor:pointer;
  font-size:15px;padding:2px 5px;line-height:1;border-radius:4px;
  transition:color .1s,background .1s;
}
.ct-icon-btn:hover{color:#e6edf3;background:#1c2128;}

/* ── Warning banner ── */
#ct-warn{
  display:none;background:rgba(240,136,62,.12);
  border-bottom:1px solid rgba(240,136,62,.35);
  padding:7px 14px;font-size:11px;color:#f0883e;flex-shrink:0;
}

/* ── Messages ── */
#ct-messages{
  flex:1;overflow-y:auto;padding:12px 14px;
  display:flex;flex-direction:column;gap:10px;
  scrollbar-width:thin;scrollbar-color:#30363d transparent;
}
#ct-messages::-webkit-scrollbar{width:4px;}
#ct-messages::-webkit-scrollbar-thumb{background:#30363d;border-radius:4px;}

.ct-msg{max-width:89%;padding:9px 12px;border-radius:10px;line-height:1.5;word-break:break-word;font-size:13px;white-space:pre-wrap;}
.ct-msg.user{align-self:flex-end;background:#f0883e;color:#fff;border-bottom-right-radius:3px;}
.ct-msg.assistant{align-self:flex-start;background:#1c2128;border:1px solid #30363d;color:#e6edf3;border-bottom-left-radius:3px;}
.ct-msg.assistant code{font-family:inherit;background:#161b22;padding:1px 5px;border-radius:3px;font-size:12px;color:#f0883e;}
.ct-msg.assistant strong{color:#fff;font-weight:600;}
.ct-msg.system{align-self:center;background:transparent;color:#8b949e;font-size:11px;font-style:italic;border:none;padding:2px 0;}

/* ── Typing indicator ── */
.ct-typing{
  align-self:flex-start;background:#1c2128;border:1px solid #30363d;
  border-radius:10px;border-bottom-left-radius:3px;
  padding:10px 14px;display:flex;gap:5px;align-items:center;
}
.ct-typing span{width:6px;height:6px;border-radius:50%;background:#8b949e;animation:ct-bounce 1.2s infinite;}
.ct-typing span:nth-child(2){animation-delay:.2s;}
.ct-typing span:nth-child(3){animation-delay:.4s;}
@keyframes ct-bounce{0%,60%,100%{transform:translateY(0);opacity:.4;}30%{transform:translateY(-5px);opacity:1;}}

/* ── Empty state ── */
#ct-empty{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  height:100%;gap:10px;color:#8b949e;font-size:12px;text-align:center;padding:24px;
}
#ct-empty .ct-logo{font-size:40px;margin-bottom:4px;}

/* ── Suggestion chips ── */
.ct-chip{
  background:#1c2128;border:1px solid #30363d;border-radius:8px;
  padding:7px 12px;cursor:pointer;font-size:11px;color:#8b949e;
  width:100%;text-align:left;transition:border-color .15s,color .15s;font-family:inherit;
}
.ct-chip:hover{border-color:#f0883e;color:#f0883e;}

/* ── Input ── */
#ct-input-area{padding:10px 12px;border-top:1px solid #30363d;display:flex;gap:8px;align-items:flex-end;background:#161b22;flex-shrink:0;}
#ct-input{
  flex:1;background:#0d1117;border:1px solid #30363d;border-radius:8px;
  color:#e6edf3;padding:8px 10px;font-family:inherit;font-size:13px;
  resize:none;min-height:36px;max-height:100px;outline:none;transition:border-color .15s;line-height:1.4;
}
#ct-input:focus{border-color:#f0883e;}
#ct-input::placeholder{color:#8b949e;}
#ct-send{
  background:#f0883e;border:none;border-radius:8px;color:#fff;width:36px;height:36px;
  cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center;
  flex-shrink:0;transition:background .15s,transform .1s;align-self:flex-end;
}
#ct-send:hover{background:#d97706;}
#ct-send:active{transform:scale(.92);}
#ct-send:disabled{opacity:.35;cursor:default;transform:none;}
"""


def _html(broker_label: str, chips: list[tuple[str, str]]) -> str:
    """
    Build the widget HTML.

    broker_label : display name shown in the header badge (e.g. "Alpaca-1")
    chips        : list of (chip_id, chip_text) for quick-start suggestions
    """
    chip_html = "".join(
        f'<button class="ct-chip" id="ct-{cid}">{text}</button>'
        for cid, text in chips
    )
    return f"""\
<div id="ct-root">
  <div id="ct-bubble" title="Open Connectors Tester AI Agent">
    <span>🔌</span>
    <div id="ct-badge"></div>
  </div>
  <div id="ct-window">
    <div id="ct-header">
      <div id="ct-title">
        <div class="ct-dot"></div>Connectors AI
      </div>
      <div id="ct-broker-badge">{broker_label}</div>
      <div class="ct-mode-pill">
        <button class="ct-mode-btn active" data-mode="chat">Chat</button>
        <button class="ct-mode-btn"        data-mode="agent">Agent</button>
      </div>
      <button class="ct-icon-btn" id="ct-clear-btn" title="Clear">🗑</button>
      <button class="ct-icon-btn" id="ct-min-btn"   title="Minimise">─</button>
    </div>
    <div id="ct-warn">⚠ Agent mode executes real broker actions — confirm every step.</div>
    <div id="ct-messages">
      <div id="ct-empty">
        <div class="ct-logo">🔌</div>
        <strong style="color:#e6edf3">Connectors Tester AI</strong>
        <p>Ask about account, positions, orders,<br>or place trades via Agent Mode.</p>
        {chip_html}
      </div>
    </div>
    <div id="ct-input-area">
      <textarea id="ct-input" placeholder="Ask anything… (Enter to send)" rows="1"></textarea>
      <button id="ct-send">&#9658;</button>
    </div>
  </div>
</div>"""


_JS_TEMPLATE = r"""
(function() {
  'use strict';
  var pdoc, pwin, pss;
  try { pdoc = window.parent.document; pwin = window.parent; pss = window.parent.sessionStorage; }
  catch(e) { pdoc = document; pwin = window; pss = sessionStorage; }

  /* API_BASE and BROKER are injected by Python before this script runs */
  var API_BASE = pwin.__CT_API    || 'http://localhost:8000';
  var BROKER   = pwin.__CT_BROKER || 'alpaca_1';
  var SS_KEY   = 'ct_state_v2';

  function tryInit(n) {
    var root = pdoc.getElementById('ct-root');
    if (!root) { if (n > 0) setTimeout(function(){ tryInit(n-1); }, 200); return; }
    if (root.dataset.ctInit === '1') return;
    root.dataset.ctInit = '1';
    init(root);
  }
  tryInit(40);

  function init(root) {
    var state = { open: false, mode: 'chat', history: [], pos: { x: 0, y: 0 } };
    try { var s = pss.getItem(SS_KEY); if (s) Object.assign(state, JSON.parse(s)); } catch(_) {}
    function save() { try { pss.setItem(SS_KEY, JSON.stringify(state)); } catch(_) {} }

    var winEl   = pdoc.getElementById('ct-window');
    var msgs    = pdoc.getElementById('ct-messages');
    var inp     = pdoc.getElementById('ct-input');
    var sendBtn = pdoc.getElementById('ct-send');
    var emptyEl = pdoc.getElementById('ct-empty');
    var warnEl  = pdoc.getElementById('ct-warn');
    var badge   = pdoc.getElementById('ct-badge');

    /* Wire all events */
    pdoc.getElementById('ct-bubble').addEventListener('click', toggle);
    pdoc.getElementById('ct-clear-btn').addEventListener('click', clearChat);
    pdoc.getElementById('ct-min-btn').addEventListener('click', toggle);
    pdoc.querySelectorAll('.ct-mode-btn').forEach(function(btn) {
      btn.addEventListener('click', function() { setMode(btn.dataset.mode); });
    });

    /* Wire suggestion chips — JS is chip-id-agnostic; we just read textContent */
    pdoc.querySelectorAll('.ct-chip').forEach(function(chip) {
      chip.addEventListener('click', function() { suggest(chip.textContent.trim()); });
    });

    sendBtn.addEventListener('click', send);
    inp.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    inp.addEventListener('input', function() { autoResize(inp); });

    /* Drag logic */
    var dragging = false, sx, sy, ox, oy;
    pdoc.getElementById('ct-header').addEventListener('mousedown', function(e) {
      if (e.target.tagName === 'BUTTON') return;
      dragging = true; sx = e.clientX; sy = e.clientY; ox = state.pos.x; oy = state.pos.y;
      e.preventDefault();
    });
    pdoc.addEventListener('mousemove', function(e) {
      if (!dragging) return;
      state.pos.x = ox + (e.clientX - sx); state.pos.y = oy + (e.clientY - sy);
      applyPos();
    });
    pdoc.addEventListener('mouseup', function() { if (dragging) { dragging = false; save(); } });

    applyMode(state.mode);
    if (state.pos.x || state.pos.y) applyPos();
    if (state.open) openWin();
    renderHistory();

    function toggle() { state.open = !state.open; save(); state.open ? openWin() : closeWin(); }
    function openWin() {
      winEl.classList.add('ct-open'); badge.style.display = 'none';
      setTimeout(function() { msgs.scrollTop = msgs.scrollHeight; inp.focus(); }, 60);
    }
    function closeWin() { winEl.classList.remove('ct-open'); }

    function setMode(m) { state.mode = m; save(); applyMode(m); }
    function applyMode(m) {
      pdoc.querySelectorAll('.ct-mode-btn').forEach(function(b) {
        b.classList.toggle('active', b.dataset.mode === m);
      });
      warnEl.style.display = (m === 'agent') ? 'block' : 'none';
    }

    function clearChat() {
      state.history = []; save();
      msgs.innerHTML = ''; msgs.appendChild(emptyEl); emptyEl.style.display = 'flex';
    }
    function suggest(text) { inp.value = text; send(); }
    function applyPos() { root.style.transform = 'translate('+state.pos.x+'px,'+state.pos.y+'px)'; }

    function send() {
      var text = inp.value.trim(); if (!text) return;
      inp.value = ''; autoResize(inp);
      addMsg('user', text);
      state.history.push({ role: 'user', content: text }); save();
      fetchReply(text);
    }

    function renderHistory() {
      if (!state.history.length) return;
      emptyEl.style.display = 'none';
      state.history.forEach(function(m) { addMsg(m.role, m.content); });
    }
    function addMsg(role, text) {
      emptyEl.style.display = 'none';
      var div = pdoc.createElement('div');
      div.className = 'ct-msg ' + role;
      div.innerHTML = (role === 'assistant') ? formatMd(text) : escHtml(text);
      msgs.appendChild(div); msgs.scrollTop = msgs.scrollHeight;
    }
    function addTyping() {
      var div = pdoc.createElement('div');
      div.className = 'ct-typing'; div.id = 'ct-typing';
      div.innerHTML = '<span></span><span></span><span></span>';
      msgs.appendChild(div); msgs.scrollTop = msgs.scrollHeight;
    }
    function removeTyping() { var el = pdoc.getElementById('ct-typing'); if (el) el.remove(); }
    function escHtml(s) {
      return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }
    function formatMd(t) {
      return escHtml(t)
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
    }
    function autoResize(el) { el.style.height='auto'; el.style.height=Math.min(el.scrollHeight,100)+'px'; }

    function fetchReply(message) {
      sendBtn.disabled = true; addTyping();
      fetch(API_BASE + '/ct/agent/chat', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ message: message, history: state.history.slice(0,-1), mode: state.mode, broker: BROKER })
      })
      .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function(d) {
        removeTyping();
        var reply = d.response || '(empty)';
        addMsg('assistant', reply);
        state.history.push({ role: 'assistant', content: reply }); save();
        if (!state.open) badge.style.display = 'block';
      })
      .catch(function(err) {
        removeTyping();
        addMsg('system', '\u26a0 ' + err.message + ' — is the Connectors Tester FastAPI server running?');
      })
      .finally(function() { sendBtn.disabled = false; inp.focus(); });
    }
  }
})();
"""


def render_connectors_agent_widget(
    broker: str = "alpaca_1",
    api_base_url: str = "http://localhost:8501",
) -> None:
    """
    Inject the floating Connectors Tester chat widget into the current Streamlit page.

    Args:
        broker      : currently selected broker ("alpaca_1" | "alpaca_2" | "mt5")
        api_base_url: base URL where the tester's FastAPI or Streamlit backend runs
    """
    import streamlit as st
    import streamlit.components.v1 as components

    # Map broker key → display label for the header badge
    broker_labels = {"alpaca_1": "Alpaca-1", "alpaca_2": "Alpaca-2", "mt5": "MT5"}
    broker_label  = broker_labels.get(broker, broker.upper())

    # Build broker-specific suggestion chips
    chips: list[tuple[str, str]] = [
        ("c1", f"Show account summary for {broker_label}"),
        ("c2", f"Show open positions"),
        ("c3", "List pending/open orders"),
        ("c4", "Show P&L summary from trade log"),
    ]

    html_block = _html(broker_label, chips)

    # Layer 1: CSS + HTML structure
    st.markdown(f"<style>{_CSS}</style>{html_block}", unsafe_allow_html=True)

    # Layer 2: JS injector (sets API_BASE and BROKER before the main script)
    api_json    = json.dumps(api_base_url)
    broker_json = json.dumps(broker)
    injector    = f"""<script>
window.parent.__CT_API    = {api_json};
window.parent.__CT_BROKER = {broker_json};
{_JS_TEMPLATE}
</script>"""

    # Collapse the iframe to zero visual height
    st.markdown(
        "<style>div[data-testid='stCustomComponentV1']{"
        "height:0!important;min-height:0!important;"
        "padding:0!important;margin:0!important;overflow:hidden!important;}"
        "</style>",
        unsafe_allow_html=True,
    )
    components.html(injector, height=1, scrolling=False)
