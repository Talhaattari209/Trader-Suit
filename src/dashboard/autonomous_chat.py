"""
Autonomous Agent — floating draggable chat widget for Streamlit.

Architecture (two-layer to survive Streamlit's HTML sanitiser):
  Layer 1 — st.markdown(unsafe_allow_html=True)
      Injects <style> CSS + the widget <div> HTML tree.
      DOMPurify allows these; onclick attrs are stripped but that's fine.

  Layer 2 — streamlit.components.v1.html(height=1)
      Runs inside a same-origin iframe; uses window.parent.document to reach
      the already-present widget elements and attaches all event listeners.
      Retries with setTimeout in case React hasn't committed the elements yet.

Chat history is stored in window.parent.sessionStorage (survives page nav).
"""
from __future__ import annotations

import json


# ── CSS ─────────────────────────────────────────────────────────────────────────
_CSS = """
#aa-root *{box-sizing:border-box;margin:0;padding:0;}
#aa-root{
  position:fixed;bottom:28px;right:28px;z-index:2147483647;
  font-family:'SF Mono','Cascadia Code',ui-monospace,monospace;font-size:13px;
}
#aa-bubble{
  width:54px;height:54px;border-radius:50%;
  background:linear-gradient(135deg,#58a6ff 0%,#388bfd 100%);
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;font-size:24px;user-select:none;
  box-shadow:0 4px 20px rgba(88,166,255,.4),0 2px 8px rgba(0,0,0,.6);
  transition:transform .15s,box-shadow .15s;
}
#aa-bubble:hover{transform:scale(1.08);box-shadow:0 6px 28px rgba(88,166,255,.55),0 3px 12px rgba(0,0,0,.7);}
#aa-badge{
  position:absolute;top:-2px;right:-2px;width:14px;height:14px;border-radius:50%;
  background:#3fb950;border:2px solid #0d1117;display:none;
}
#aa-window{
  position:absolute;bottom:66px;right:0;width:385px;height:545px;
  background:#0d1117;border:1px solid #30363d;border-radius:14px;
  display:flex;flex-direction:column;overflow:hidden;
  box-shadow:0 24px 60px rgba(0,0,0,.8),0 4px 16px rgba(0,0,0,.5);
  opacity:0;transform:translateY(8px) scale(.97);pointer-events:none;
  transition:opacity .2s ease,transform .2s ease;
}
#aa-window.aa-open{opacity:1;transform:translateY(0) scale(1);pointer-events:all;}
#aa-header{
  background:#161b22;border-bottom:1px solid #30363d;
  padding:10px 14px;display:flex;align-items:center;gap:8px;
  cursor:grab;user-select:none;flex-shrink:0;
}
#aa-header:active{cursor:grabbing;}
#aa-title{
  flex:1;font-weight:600;font-size:12px;letter-spacing:.06em;
  text-transform:uppercase;color:#e6edf3;display:flex;align-items:center;gap:6px;
}
.aa-dot{width:7px;height:7px;border-radius:50%;background:#3fb950;box-shadow:0 0 6px #3fb950;}
.aa-mode-pill{display:flex;background:#0d1117;border:1px solid #30363d;border-radius:20px;overflow:hidden;}
.aa-mode-btn{
  padding:3px 10px;font-size:11px;font-weight:600;letter-spacing:.04em;
  text-transform:uppercase;cursor:pointer;color:#8b949e;border:none;background:transparent;
  transition:background .15s,color .15s;
}
.aa-mode-btn.active[data-mode="chat"]{background:#58a6ff;color:#fff;border-radius:20px;}
.aa-mode-btn.active[data-mode="agent"]{background:#d2a8ff;color:#0d1117;border-radius:20px;}
.aa-icon-btn{
  background:none;border:none;color:#8b949e;cursor:pointer;
  font-size:15px;padding:2px 4px;line-height:1;border-radius:4px;
  transition:color .1s,background .1s;
}
.aa-icon-btn:hover{color:#e6edf3;background:#1c2128;}
#aa-warn{
  display:none;background:rgba(240,136,62,.12);border-bottom:1px solid rgba(240,136,62,.35);
  padding:6px 14px;font-size:11px;color:#f0883e;flex-shrink:0;
}
#aa-messages{
  flex:1;overflow-y:auto;padding:12px 14px;
  display:flex;flex-direction:column;gap:10px;
  scrollbar-width:thin;scrollbar-color:#30363d transparent;
}
#aa-messages::-webkit-scrollbar{width:4px;}
#aa-messages::-webkit-scrollbar-thumb{background:#30363d;border-radius:4px;}
.aa-msg{max-width:88%;padding:9px 12px;border-radius:10px;line-height:1.5;word-break:break-word;font-size:13px;white-space:pre-wrap;}
.aa-msg.user{align-self:flex-end;background:#58a6ff;color:#fff;border-bottom-right-radius:3px;}
.aa-msg.assistant{align-self:flex-start;background:#1c2128;border:1px solid #30363d;color:#e6edf3;border-bottom-left-radius:3px;}
.aa-msg.assistant code{font-family:inherit;background:#161b22;padding:1px 5px;border-radius:3px;font-size:12px;color:#58a6ff;}
.aa-msg.assistant strong{color:#fff;font-weight:600;}
.aa-msg.system{align-self:center;background:transparent;color:#8b949e;font-size:11px;font-style:italic;border:none;padding:2px 0;}
.aa-typing{align-self:flex-start;background:#1c2128;border:1px solid #30363d;border-radius:10px;border-bottom-left-radius:3px;padding:10px 14px;display:flex;gap:5px;align-items:center;}
.aa-typing span{width:6px;height:6px;border-radius:50%;background:#8b949e;animation:aa-bounce 1.2s infinite;}
.aa-typing span:nth-child(2){animation-delay:.2s;}
.aa-typing span:nth-child(3){animation-delay:.4s;}
@keyframes aa-bounce{0%,60%,100%{transform:translateY(0);opacity:.4;}30%{transform:translateY(-5px);opacity:1;}}
#aa-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:10px;color:#8b949e;font-size:12px;text-align:center;padding:24px;}
#aa-empty .aa-logo{font-size:38px;margin-bottom:4px;}
#aa-empty p{opacity:.7;line-height:1.6;}
.aa-chip{background:#1c2128;border:1px solid #30363d;border-radius:8px;padding:6px 12px;cursor:pointer;font-size:11px;color:#8b949e;width:100%;text-align:left;transition:border-color .15s,color .15s;font-family:inherit;}
.aa-chip:hover{border-color:#58a6ff;color:#58a6ff;}
#aa-input-area{padding:10px 12px;border-top:1px solid #30363d;display:flex;gap:8px;align-items:flex-end;background:#161b22;flex-shrink:0;}
#aa-input{flex:1;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#e6edf3;padding:8px 10px;font-family:inherit;font-size:13px;resize:none;min-height:36px;max-height:100px;outline:none;transition:border-color .15s;line-height:1.4;}
#aa-input:focus{border-color:#58a6ff;}
#aa-input::placeholder{color:#8b949e;}
#aa-send{background:#58a6ff;border:none;border-radius:8px;color:#fff;width:36px;height:36px;cursor:pointer;font-size:17px;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:background .15s,transform .1s;align-self:flex-end;}
#aa-send:hover{background:#388bfd;}
#aa-send:active{transform:scale(.92);}
#aa-send:disabled{opacity:.35;cursor:default;transform:none;}
"""

# ── Widget HTML (no onclick attrs — event listeners attached by JS layer) ────────
_HTML = """\
<div id="aa-root">
  <div id="aa-bubble" title="Open AI Agent"><span>🤖</span><div id="aa-badge"></div></div>
  <div id="aa-window">
    <div id="aa-header">
      <div id="aa-title"><div class="aa-dot"></div>Trader-Suit AI</div>
      <div class="aa-mode-pill">
        <button class="aa-mode-btn active" data-mode="chat">Chat</button>
        <button class="aa-mode-btn" data-mode="agent">Agent</button>
      </div>
      <button class="aa-icon-btn" id="aa-clear-btn" title="Clear">🗑</button>
      <button class="aa-icon-btn" id="aa-min-btn" title="Minimise">─</button>
    </div>
    <div id="aa-warn">⚠ Agent mode can execute real actions — confirm each step.</div>
    <div id="aa-messages">
      <div id="aa-empty">
        <div class="aa-logo">🤖</div>
        <strong style="color:#e6edf3">Trader-Suit AI Assistant</strong>
        <p>Ask about strategies, positions,<br>price levels, or the vault.</p>
        <button class="aa-chip" id="aa-s1">📊 Show open positions</button>
        <button class="aa-chip" id="aa-s2">⚙️ Current workflow state</button>
        <button class="aa-chip" id="aa-s3">📈 List production strategies</button>
        <button class="aa-chip" id="aa-s4">🎯 US30 price levels</button>
      </div>
    </div>
    <div id="aa-input-area">
      <textarea id="aa-input" placeholder="Ask anything… (Enter to send)" rows="1"></textarea>
      <button id="aa-send">&#9658;</button>
    </div>
  </div>
</div>"""

# ── JS (runs in child iframe; all DOM ops via window.parent.document) ────────────
# NOTE: this is a raw string; API_BASE is injected as a JS variable by the caller.
_JS = r"""
(function() {
  var pdoc, pwin, pss;
  try { pdoc = window.parent.document; pwin = window.parent; pss = window.parent.sessionStorage; }
  catch(e) { pdoc = document; pwin = window; pss = sessionStorage; }

  var API_BASE = pwin.__AA_API || 'http://localhost:8000';
  var SS_KEY   = 'aa_state_v2';

  /* ── Retry until HTML is ready ───────────────────────────────────────────── */
  function tryInit(n) {
    var root = pdoc.getElementById('aa-root');
    if (!root) { if (n > 0) setTimeout(function(){ tryInit(n-1); }, 200); return; }
    if (root.dataset.aaInit === '1') return;   // already running
    root.dataset.aaInit = '1';
    init(root);
  }
  tryInit(40);  // ~8 seconds of retries

  function init(root) {
    /* ── State ─────────────────────────────────────────────────────────────── */
    var state = { open: false, mode: 'chat', history: [], pos: { x: 0, y: 0 } };
    try { var s = pss.getItem(SS_KEY); if (s) Object.assign(state, JSON.parse(s)); } catch(_) {}
    function save() { try { pss.setItem(SS_KEY, JSON.stringify(state)); } catch(_) {} }

    /* ── DOM refs ───────────────────────────────────────────────────────────── */
    var win_el  = pdoc.getElementById('aa-window');
    var msgs    = pdoc.getElementById('aa-messages');
    var inp     = pdoc.getElementById('aa-input');
    var sendBtn = pdoc.getElementById('aa-send');
    var empty   = pdoc.getElementById('aa-empty');
    var warn    = pdoc.getElementById('aa-warn');
    var badge   = pdoc.getElementById('aa-badge');

    /* ── Wire events ────────────────────────────────────────────────────────── */
    pdoc.getElementById('aa-bubble').addEventListener('click', toggle);
    pdoc.getElementById('aa-clear-btn').addEventListener('click', clearChat);
    pdoc.getElementById('aa-min-btn').addEventListener('click', toggle);
    pdoc.querySelectorAll('.aa-mode-btn').forEach(function(b) {
      b.addEventListener('click', function() { setMode(b.dataset.mode); });
    });
    pdoc.getElementById('aa-s1').addEventListener('click', function(){ suggest('Show me open positions'); });
    pdoc.getElementById('aa-s2').addEventListener('click', function(){ suggest('What is the current workflow state?'); });
    pdoc.getElementById('aa-s3').addEventListener('click', function(){ suggest('List all production strategies'); });
    pdoc.getElementById('aa-s4').addEventListener('click', function(){ suggest('What price levels are detected on US30?'); });
    sendBtn.addEventListener('click', send);
    inp.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    inp.addEventListener('input', function() { autoResize(inp); });

    /* ── Drag ───────────────────────────────────────────────────────────────── */
    var drag = false, dsx, dsy, ox, oy;
    pdoc.getElementById('aa-header').addEventListener('mousedown', function(e) {
      if (e.target.tagName === 'BUTTON') return;
      drag = true; dsx = e.clientX; dsy = e.clientY; ox = state.pos.x; oy = state.pos.y;
      e.preventDefault();
    });
    pdoc.addEventListener('mousemove', function(e) {
      if (!drag) return;
      state.pos.x = ox + (e.clientX - dsx); state.pos.y = oy + (e.clientY - dsy);
      applyPos();
    });
    pdoc.addEventListener('mouseup', function() { if (drag) { drag = false; save(); } });

    /* ── Apply saved state ─────────────────────────────────────────────────── */
    applyMode(state.mode);
    if (state.pos.x || state.pos.y) applyPos();
    if (state.open) openWin();
    renderHistory();

    /* ── Functions ──────────────────────────────────────────────────────────── */
    function toggle() { state.open = !state.open; save(); if (state.open) openWin(); else closeWin(); }
    function openWin() {
      win_el.classList.add('aa-open'); badge.style.display = 'none';
      setTimeout(function() { msgs.scrollTop = msgs.scrollHeight; inp.focus(); }, 60);
    }
    function closeWin() { win_el.classList.remove('aa-open'); }

    function setMode(m) { state.mode = m; save(); applyMode(m); }
    function applyMode(m) {
      pdoc.querySelectorAll('.aa-mode-btn').forEach(function(b) {
        b.classList.toggle('active', b.dataset.mode === m);
      });
      warn.style.display = m === 'agent' ? 'block' : 'none';
    }

    function clearChat() {
      state.history = []; save();
      msgs.innerHTML = ''; msgs.appendChild(empty); empty.style.display = 'flex';
    }
    function suggest(t) { inp.value = t; send(); }
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
      empty.style.display = 'none';
      state.history.forEach(function(m) { addMsg(m.role, m.content); });
    }
    function addMsg(role, text) {
      empty.style.display = 'none';
      var div = pdoc.createElement('div');
      div.className = 'aa-msg ' + role;
      div.innerHTML = role === 'assistant' ? formatMd(text) : esc(text);
      msgs.appendChild(div); msgs.scrollTop = msgs.scrollHeight;
    }
    function addTyping() {
      var div = pdoc.createElement('div');
      div.className = 'aa-typing'; div.id = 'aa-typing';
      div.innerHTML = '<span></span><span></span><span></span>';
      msgs.appendChild(div); msgs.scrollTop = msgs.scrollHeight;
    }
    function removeTyping() { var el = pdoc.getElementById('aa-typing'); if (el) el.remove(); }
    function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    function formatMd(t) {
      return esc(t)
        .replace(/[*][*](.+?)[*][*]/g,'<strong>$1</strong>')
        .replace(/`([^`]+)`/g,'<code>$1</code>')
        .replace(/\n/g,'<br>');
    }
    function autoResize(el) { el.style.height='auto'; el.style.height=Math.min(el.scrollHeight,100)+'px'; }

    function fetchReply(message) {
      sendBtn.disabled = true; addTyping();
      fetch(API_BASE + '/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message, history: state.history.slice(0,-1), mode: state.mode })
      })
      .then(function(r) { if (!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
      .then(function(d) {
        removeTyping();
        var reply = d.response || '(no response)';
        addMsg('assistant', reply);
        state.history.push({ role:'assistant', content:reply }); save();
        if (!state.open) badge.style.display = 'block';
      })
      .catch(function(err) {
        removeTyping();
        addMsg('system', '\u26a0 ' + err.message + ' — is the FastAPI backend running?');
      })
      .finally(function() { sendBtn.disabled = false; inp.focus(); });
    }
  } // end init()
})();
"""


def render_autonomous_agent_widget(api_base_url: str = "http://localhost:8000") -> None:
    """
    Render the floating AI Agent chat widget on every Streamlit page.

    Two-layer injection:
      1. st.markdown  → CSS + HTML div structure (always rendered by Streamlit)
      2. components.v1.html height=1 → tiny script that finds the div in
         window.parent.document and attaches all JS event listeners.

    Args:
        api_base_url: Base URL of the FastAPI backend.
    """
    import streamlit as st
    import streamlit.components.v1 as components

    # Layer 1: CSS + HTML (DOMPurify-safe — no script, no onclick attrs)
    st.markdown(
        f"<style>{_CSS}</style>{_HTML}",
        unsafe_allow_html=True,
    )

    # Layer 2: JS — runs in same-origin iframe, wires event listeners via window.parent
    api_json = json.dumps(api_base_url)
    injector = f"""<script>
window.parent.__AA_API = {api_json};
{_JS}
</script>"""

    # height=1 ensures the iframe is rendered and scripts execute
    # The 1px gap is collapsed by the CSS rule below (injected via st.markdown)
    st.markdown(
        "<style>"
        "div[data-testid='stCustomComponentV1']{height:0!important;min-height:0!important;"
        "padding:0!important;margin:0!important;overflow:hidden!important;}"
        "</style>",
        unsafe_allow_html=True,
    )
    components.html(injector, height=1, scrolling=False)
