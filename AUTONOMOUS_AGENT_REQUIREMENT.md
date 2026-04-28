**AUTONOMOUS_AGENT_REQUIREMENT.md**  
**Project: Trader-Suit / OpenClaw Alpha Research System**  
**Client Requirement – Autonomous AI Agent (Chat + Agent Modes)**  

> **Instruction to Cursor Agent (Sonnet / Opus 4.6)**  
> You are now implementing the **new client requirement** exactly as described below.  
> This must be added on top of all previous improvements (UV environment, filesystem-only persistence, price_levels detector, human-controlled workflow, full FastAPI endpoints, SHAP, performance metrics, LLM/MCP console debugging, two Alpaca accounts, etc.).  
> **Goal**: Deliver a fully working autonomous AI agent that appears on **every page** of the Streamlit dashboard as a **movable floating widget** at the bottom-right.  

---

### 1. Exact Client Requirement

**Feature**: Autonomous Agent on the website  
- User can **chat** with the system and get **any information** about:  
  - Orders  
  - Open positions  
  - Strategies (drafts, production, graveyard)  
  - Trade logs  
  - Indicators  
  - Parameters  
  - Strategy code  
  - Price levels (liquidity zones, FVG, session/day/week/month highs/lows/mids/opens/closes)  
  - Risk audits, Monte Carlo results, performance metrics, SHAP analysis  
  - **Everything** in the system (vault, DataStore, logs, etc.)

**Two Modes** (toggle switch inside the widget):
- **Chat Mode** (default) → Read-only conversation and information retrieval.  
- **Agent Mode** → Full autonomous execution: can trigger workflows, run Monte Carlo, approve strategies, move files, execute paper/live orders (with HITL safeguards), etc.

**UI Placement**:
- Floating widget anchored at **bottom-right** of **every page**.
- **Movable / draggable** anywhere on the screen.
- Always visible (persistent across all pages).
- Clean, modern chat UI with mode toggle, clear button, and minimize option.

---

### 2. Technical Implementation Plan (Follow Exactly)

#### 2.1 UI – Floating Draggable Chat Widget (Streamlit)

Create a **single reusable component** `src/dashboard/components/autonomous_chat.py`.

- Use **custom CSS + JavaScript** for the floating draggable container (no heavy new dependencies).
- Add the following to `src/dashboard/app.py` (and ensure it runs on every page):
  ```python
  from src.dashboard.components.autonomous_chat import render_autonomous_agent_widget
  render_autonomous_agent_widget()
  ```
- The widget must:
  - Start as a small circular **chat bubble icon** (bottom-right, fixed position).
  - On click → expand into a draggable chat window (title bar + chat messages + input + mode toggle).
  - Draggable via mouse (use simple JS drag logic with `pointer-events` and `transform`).
  - Persist position using `st.session_state`.
  - Work on all 9 dashboard pages.

Recommended minimal implementation (proven in Streamlit community):
- Use `st.markdown(unsafe_allow_html=True)` with a floating `<div>` + Tailwind-like CSS.
- Or integrate `streamlit-elements` only if needed for advanced drag (but prefer pure CSS/JS first).

#### 2.2 Backend – Autonomous Agent

Create new module: `src/agents/autonomous_agent.py`

- Powered by existing `llm_client.py` (Claude/Gemini).
- **Tool-calling enabled** (extend the existing MCP style).
- In **Chat Mode**: only read operations (get data, explain, summarize).
- In **Agent Mode**: can call real actions via FastAPI tools:
  - Trigger `/workflow/start`
  - Run Monte Carlo
  - Human decision simulation (ask user confirmation inside chat)
  - Get strategies, positions, logs, price_levels, SHAP, etc.
  - Execute paper orders (never live without explicit HITL)

Add new FastAPI endpoints in `src/api/main.py` (or new `src/api/agent_routes.py`):
- `POST /agent/chat` → handles both modes
- `POST /agent/tools/{tool_name}` → secure tool execution

#### 2.3 Integration Points (Must Wire)

- Use existing `FilesystemStore` for all data access.
- Reuse `price_level_detector.py`, `performance_metrics.py`, SHAP, etc.
- In Agent Mode, the LLM can call the same workflow endpoints created in previous plans (`/workflow/*`).
- Console debugging: Every autonomous agent LLM call and tool response must print with `=== AUTONOMOUS AGENT PROMPT ===` and `=== AUTONOMOUS AGENT RESPONSE ===` (same style as existing LLM/MCP debug).

#### 2.4 Mode Switching & Safety

- Clear toggle switch in the chat header: **Chat** ↔ **Agent**
- In Agent Mode show warning banner: “Agent mode can execute real actions – confirm before proceeding.”
- All execution actions must still respect HITL (Approved/ folder) and user confirmation inside the chat.

#### 2.5 Session & State

- Use `st.session_state` to keep chat history per page (or global).
- Support multi-turn conversation with memory (inject system prompt with full system context from bootstrap + current vault state).

---

### 3. Files to Create / Update

**New files:**
- `src/dashboard/components/autonomous_chat.py` (the floating widget)
- `src/agents/autonomous_agent.py` (core logic + tools)
- `src/api/agent_routes.py` (new FastAPI router)

**Must update:**
- `src/dashboard/app.py` → import and render the widget on every page
- `src/api/main.py` → include new agent routes
- `src/tools/llm_client.py` → extend for autonomous agent (add debug prints)
- `.env.example` → add any new keys if needed (none expected)
- Update `pyproject.toml` / requirements if any tiny helper is needed (prefer zero new deps)

---

### 4. Testing Requirements

After implementation:
- Run `uv run python main.py` + `uv run streamlit run src/dashboard/app.py`
- On **any page**, click the bottom-right bubble → chat should open and be draggable.
- Test both modes:
  - Chat mode: “Show me open positions”, “What are the current price_levels?”, “Explain this strategy code”
  - Agent mode: “Run Monte Carlo on the latest strategy”, “Start a new workflow with this idea: …”
- Confirm console shows full LLM debug for every autonomous call.
- Confirm the widget does **not** break any existing page layout.

---

### 5. Final Instructions

Implement this **as a complete, production-ready feature** that feels like a built-in Copilot for the entire Trader-Suit platform.  
Make the chat UI beautiful, responsive, and professional (dark theme matching the dashboard).  

Start by creating the floating widget component first, then the backend agent, then wire the FastAPI endpoints, and finally integrate into the main app.

This is the final major client feature. Make it excellent.

**Begin implementation now.**