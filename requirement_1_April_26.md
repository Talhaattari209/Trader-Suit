**UPDATED_IMPROVEMENT_PLAN.md**  
**Project: Trader-Suit / OpenClaw Alpha Research System**  
**Version: 2026-04-01 — End-to-End Workflow Test + Price Levels Clarification**  

> **Instruction to Cursor Agent (Sonnet / Opus 4.6)**  
> You are the lead architect and implementer. **Primary goal**: Make the entire project runnable **end-to-end from the Streamlit UI** so a user can test the full human-controlled workflow today.  
> Incorporate the **exact definition of `price_levels`** provided by the user (liquidity zones, FVG zones, high/low/mid/Open/close of session/day/week/month). These are the **market-respected levels** that must be automatically detected, recorded, and used for strategy comparison/preservation.  
> All previous instructions (UV, local-first, filesystem-only, LLM/MCP console debugging, parallel where safe, two Alpaca accounts, SHAP, full metrics, human decision gate) remain in force.  

---

### 1. New End-to-End Human-Controlled Workflow (Implement This Exact Sequence)

1. **User enters Idea** (Alpha Idea Lab).  
2. **System compares** with existing alphas (using `DataStore/alphas.json` + full metadata including **price_levels**). Shows similarity + any matching strategy.  
3. **User feedback** (“Use existing”, “Create new”, “Merge”, “Discard”).  
4. **If new/merge**: Strategist generates/re-uses code **and automatically extracts current price_levels**.  
5. **System compares** new strategy code + metadata against existing.  
6. **Killer runs MonteCarloPro** (raw strategy — **no risk yet**).  
7. **Human Decision Gate** (Backtester & Killer page): Discard / Retest with feedback / Approve as-is / Approve with tweaks.  
8. **If approved**: Risk Architect applies sizing.  
9. **HITL** (Approved/ file).  
10. **Execution** + Reporter.

**Trigger everything via new `/workflow/*` FastAPI endpoints.**

---

### 2. Price Levels Definition & Implementation (MANDATORY)

**User definition (record exactly this structure):**  
`price_levels` = **liquidity zones**, **FVG zones**, **high/low/mid/Open/close of session, day, week, month**.  
These are the levels the market respects → must be **automatically detected and stored** with every alpha/strategy.

**New structured metadata (add to every strategy and alpha record):**
```json
"price_levels": {
  "liquidity_zones": [
    {"type": "demand", "price": 42350.0, "strength": "high"},
    {"type": "supply", "price": 42800.0, "strength": "medium"}
  ],
  "fvg_zones": [
    {"type": "bullish", "low": 42100.0, "high": 42250.0, "timestamp": "2026-04-01T09:30"},
    {"type": "bearish", "low": 42700.0, "high": 42850.0, "timestamp": "2026-04-01T14:00"}
  ],
  "session_levels": {
    "us_open": {"open": 42450.0, "high": 42700.0, "low": 42300.0, "close": 42600.0, "mid": 42500.0},
    "us_session": {"high": 42800.0, "low": 42200.0, "mid": 42500.0},
    "day": {"open": 42400.0, "high": 42800.0, "low": 42200.0, "close": 42650.0, "mid": 42500.0},
    "week": {"open": 42000.0, "high": 43000.0, "low": 41800.0, "mid": 42400.0},
    "month": {"open": 41500.0, "high": 43200.0, "low": 41000.0, "mid": 42100.0}
  }
}
```

**Implementation requirements:**
- Create `src/tools/price_level_detector.py` (new file).  
  - Use `US30Loader` + pandas to detect:  
    - Liquidity zones → previous swing highs/lows + volume profile.  
    - FVG zones → standard 3-candle imbalance (high of candle 1 vs low of candle 3).  
    - Session/day/week/month levels → `resample` + `ohlc`.  
- Call this automatically in Strategist Agent (after code generation) and in Killer Agent (after MC).  
- Store in `DataStore/alphas.json` and inside each strategy `.py` file as a class attribute (`self.price_levels = {...}`).  
- Use these fields for **comparison** (cosine similarity on numeric levels + exact regime/session match).

---

### 3. Answer to Risk Mechanism Timing (Confirmed)

**Apply risk (fractional Kelly, etc.) AFTER Monte Carlo?**  
**YES — keep current order.**  

**Reason**: Monte Carlo validates the **raw edge**. Applying risk first would hide whether the alpha itself is robust. Human sees clean MC results → then decides → then Risk Architect layers sizing. This matches professional quant practice and gives better post-mortems.

---

### 4. Core Technical Changes

**4.1 UV Environment**  
- Full `uv` migration (venv, compile, `uv run` commands).  

**4.2 Filesystem-Only Persistence**  
- `src/persistence/filesystem_store.py` handles all data (including new `price_levels`).  
- `DataStore/` now contains `alphas.json` with full price_levels metadata.

**4.3 Improve Parameter Stability**  
- MonteCarloPro: add ±10% parameter perturbation + stability score.  
- Killer: run walk-forward + flag unstable params.  
- Display stability heatmap + price_levels in Strategy Library.

**4.4 Two Alpaca Accounts**  
- `.env` keys for account 1 & 2.  
- Dropdown in Execution page + cockpit.

**4.5 LLM & MCP Debugging**  
- Every call prints full prompt/response + timestamp to console + `logs/debug.log`.

**4.6 Parallel (Light Version)**  
- Parallel hypothesis comparison + parallel MC on ensemble drafts.

**4.7 Complete FastAPI Endpoints** (all must be wired)  
- `/workflow/start`, `/workflow/feedback`, `/workflow/decision`  
- `/montecarlo/run`, `/shap/analyze`, `/performance/metrics/{id}`  
- `/data/alphas`, `/vault/*`, `/accounts`

**4.8 Performance Metrics** (`src/tools/performance_metrics.py`)  
- Sharpe, Sortino, Calmar, Profit Factor, Win Rate, Expectancy, Max DD, e-Ratio, Omega, regime-specific, **stability score**.

**4.9 SHAP Analysis**  
- Button in Strategy Library & Optimization Lab → `shap` on features or regime classifier.

---

### 5. UI Pages to Make Fully Functional (Focus for End-to-End Test)

1. **Alpha Idea Lab** → idea input + comparison report (with price_levels) + feedback form.  
2. **Backtester & Killer** → MC run + **Human Decision panel** (discard/retest/approve/tweak) + price_levels display.  
3. **Strategy Library** → real list + metrics cards + equity curve + price_levels table + SHAP button.  
4. **Execution & Reports** → account selector + live positions.  
5. **Home** → summary + recent workflow status.

All pages call FastAPI via `httpx`.

---

### 6. Testing Command (Verify End-to-End Today)

```bash
uv run python main.py                  # FastAPI
uv run streamlit run src/dashboard/app.py   # UI
```

**Test flow**:  
1. Enter idea in Alpha Idea Lab.  
2. Review comparison (price_levels shown).  
3. Give feedback → generate strategy.  
4. Run MC → Human decision → approve → Risk → (paper) execution.  
5. Confirm console shows LLM + MCP debug + price_levels recorded.

---

### 7. Files to Create / Update

**New files:**
- `src/tools/price_level_detector.py`
- `src/persistence/filesystem_store.py`
- `src/tools/performance_metrics.py`
- `src/api/workflow_routes.py`

**Major updates:**
- All agents (add price_levels extraction + metadata)
- `src/dashboard/pages/` (especially 1_Alpha_Idea_Lab.py, 5_Backtester_Killer.py, 4_Strategy_Library.py)
- `src/api/main.py`
- `src/tools/llm_client.py`, `src/mcp/alpaca_server.py`
- `.env.example`, `pyproject.toml`, `requirements.in`

---

**Cursor Agent — Execute in this exact order**  
1. UV + filesystem store + price_level_detector.  
2. Update agents & orchestrator with new workflow + price_levels metadata.  
3. FastAPI endpoints + metrics + SHAP.  
4. Multi-Alpaca support.  
5. Wire the 5 critical UI pages.  
6. Add debug prints + parameter stability.  
7. Test one full cycle from UI and confirm **price_levels are recorded and visible**.

This plan now gives you a **fully testable end-to-end system** with **strong human control**, clear metrics, SHAP explainability, and **precise recording of market-respected price levels** (liquidity, FVG, session/day/week/month highs/lows/mids/opens/closes).

Start implementing — we need the workflow working end-to-end today.