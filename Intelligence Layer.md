# Intelligence Layer: Librarian & Strategist

## Overview
The Intelligence Layer acts as the "Prefrontal Cortex" of the AI Employee. It bridges the gap between raw signals (Watchers) and validated strategies via the Killer Agent (Validation).

## Components

### 1. Librarian Agent (The Researcher)
**Role:** Senior Quantitative Researcher.
**Goal:** Ingest raw information and formulate a coherent Trading Hypothesis or Research Plan.
**Inputs:** `AI_Employee_Vault/Needs_Action/*.md` (files created by watchers).
**Process:**
1.  **Monitor**: Watches `Needs_Action` for new files (PDFs, News, Data).
2.  **Analyze**: Uses LLM (Claude) to extract:
    *   Alpha Signals
    *   Timeframe / Asset Class
    *   Risk Factors
3.  **Output**: Creates a `RESEARCH_PLAN_<Topic>.md` in `AI_Employee_Vault/Plans/`.

### 2. Strategist Agent (The Coder)
**Role:** Algorithmic Trader / Python Developer.
**Goal:** Translate a Research Plan into an executable Python Strategy.
**Inputs:** `AI_Employee_Vault/Plans/RESEARCH_PLAN_*.md`.
**Process:**
1.  **Monitor**: Watches `Plans` for new research plans.
2.  **Code**:
    *   Reads the Plan.
    *   Loads `US30Loader` for data context.
    *   Implements `BaseStrategy` methods (`entry`, `exit`, `risk`).
3.  **Output**: Saves `strategy_<name>.py` to `src/models/drafts/`.

### 3. Orchestration (Ralph Wiggum Loop)
**Role:** System loop manager.
**Logic:**
```python
while True:
    run_watchers()      # Ingest -> Needs_Action
    run_librarian()     # Needs_Action -> Plans
    run_strategist()    # Plans -> Drafts/
    run_killer_agent()  # Drafts/ -> Risk_Audit
    sleep(60)
```

## Interaction Flow
`[World]` -> **Watchers** -> `[Needs_Action]` -> **Librarian** -> `[Plans]` -> **Strategist** -> `[Drafts]` -> **Killer Agent** -> `[Logs/Done]`
