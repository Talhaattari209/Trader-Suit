# Full Implementation Plan — Autonomous Alpha Research FTE

**Motive (Code-as-Interface):** In future, when the user gives a prompt, the **System shall code instructions (strategy, research plan, or anything else) itself**, and the **User only reviews**. This plan aligns the folder structure and implementation with that goal.

**References:** `specs.md`, `code_as_interface.md`, `claude_code_plan.md`

---

## 1. What Is Already Implemented

### 1.1 BaseWatcher (Phase 1 — verified)

| File | Status | Notes |
|------|--------|--------|
| `src/watchers/base_watcher.py` | Done | ABC with `vault_path`, `needs_action`, `check_for_updates()`, `create_action_file()`, `run()` loop. Solid base. |

**Spec alignment:** Spec says *"Implement the BaseWatcher in Python to detect new files in /Needs_Action"*. Current design is: watchers watch **external source folders** and **create** structured `.md` files **in** `/Needs_Action` for Claude to process. So the system “detects” new work by creating action files from external inputs. That matches `claude_code_plan.md` (“Watchers create structured markdown files in /Needs_Action”). No change required to BaseWatcher for Phase 1; optional later: a small **Needs_ActionWatcher** that only reacts to files dropped directly into `/Needs_Action` (e.g. user-dropped PDFs).

### 1.2 Concrete watchers

| File | Status | Notes |
|------|--------|--------|
| `src/watchers/research_watcher.py` | Done | Watches `research_input_path` for `.md`, `.txt`, `.pdf`; copies to `Research_Data`, creates `RESEARCH_*.md` in `Needs_Action` with frontmatter. |
| `src/watchers/dat-ingestion_watcher.py` | Done | Watches `data_source_path` for `.csv`, `.json`; copies to `Research_Data`, creates `DATA_*.md` in `Needs_Action`. |

**Naming fix:** File is `dat-ingestion_watcher.py` (missing ‘a’). Frontmatter has `type: market_dat-ingestion`. Recommend: rename to `data_ingestion_watcher.py` and use `type: market_data_ingestion`.

### 1.3 Database

| File | Status | Notes |
|------|--------|--------|
| `database/schema.sql` | Done | Tables: `alphas`, `strategy_graveyard`, `market_regimes`, `agent_audit_logs`. Matches specs + audit. |

### 1.4 Vault

| Item | Status | Notes |
|------|--------|--------|
| `AI_Employee_Vault/` | Partial | Exists with `.obsidian/` and `Welcome.md`. **Folder structure below not yet created.** |

### 1.5 Dependencies

| File | Status | Notes |
|------|--------|--------|
| `requirements.txt` | Partial | Only `asyncpg`. Will need more as you add agents, MCP, RL, etc. |

---

## 2. What Is Not Implemented (and where it lives)

- **Phase 1:** `db_handler.py`, full **Obsidian Vault folder structure**.
- **Phase 2+:** Monte Carlo tool, US30 data loader, Ralph Wiggum loop, Librarian/Strategist/Monte Carlo/Regime/Risk agents, MCP servers, `src/models/drafts/`, orchestration.

---

## 3. Changes Recommended Before You Implement Folders

1. **Rename** `src/watchers/dat-ingestion_watcher.py` → `src/watchers/data_ingestion_watcher.py` and fix frontmatter `type` to `market_data_ingestion`.
2. **Add** `src/watchers/__init__.py` (e.g. export `BaseWatcher`, `ResearchWatcher`, `DataIngestionWatcher`) for clean imports.
3. **Optional:** Add a **Needs_ActionWatcher** that only watches `/Needs_Action` for files dropped directly by the user (PDFs, URLs, text) so “prompt in the form of a file” is supported; other watchers stay as “external source → action file” creators.

---

## 4. Folder Structure To Implement Yourself

Below is the full structure so you can create it manually. It supports: (a) specs + `claude_code_plan.md`, and (b) **code-as-interface**: system-generated code/plans live in clear places and the user reviews before approval.

### 4.1 Obsidian Vault — `AI_Employee_Vault/`

Create these **folders** (and keep existing `.obsidian/` and `Welcome.md`):

```
AI_Employee_Vault/
├── .obsidian/                    # already exists
├── Welcome.md                    # already exists
│
├── Needs_Action/                 # Inbox: action .md files for Claude (from watchers or user drops)
├── Plans/                        # System-generated research plans (e.g. RESEARCH_PLAN.md) — user reviews here
├── Done/                         # Completed tasks / research
├── Logs/                         # Audit logs of AI actions (e.g. data_processed.log, research_processed.log)
├── Pending_Approval/             # Code/strategy/actions requiring human review (HITL)
├── Approved/                    # Human-approved (e.g. move to live)
├── Rejected/                     # Human-rejected
├── Accounting/                   # Financial transactions and reports
├── Research_Data/                # Raw market data, research papers (watchers copy here)
├── Alphas/                       # Validated strategy parameters (links to DB + local notes)
├── Strategy_Graveyard/           # Failed hypotheses (links to DB + local notes)
├── Market_Regimes/               # Metadata on historical market periods (reference)
│
├── Needs_Action/ResearchInput/   # Optional: drop research files here → ResearchWatcher picks up
├── Needs_Action/DataSource/      # Optional: drop CSV/JSON here → DataIngestionWatcher picks up
│
└── (initial markdown — create as needed)
    ├── Dashboard.md
    ├── Company_Handbook.md       # Trading rules / risk limits
    └── Business_Goals.md         # Trading objectives
```

**Code-as-interface:**  
- **System-generated “code” (plans/strategies):** `Plans/` (research plans), later `src/models/drafts/` (Python strategies).  
- **User review:** Move from `Pending_Approval/` to `Approved/` or `Rejected/`.  
- **Instructions from prompt:** Can land as new `.md` in `Needs_Action/` (from a future “prompt watcher” or manual drop), then system writes code/plan into `Plans/` or `src/models/drafts/` and puts review items in `Pending_Approval/`.

### 4.2 Project root — `src/`, `database/`, config

```
c:\Users\User\Downloads\claude\
├── AI_Employee_Vault/            # (structure above)
├── database/
│   └── schema.sql                # already exists
├── src/
│   ├── watchers/
│   │   ├── __init__.py           # ADD: export BaseWatcher, ResearchWatcher, DataIngestionWatcher
│   │   ├── base_watcher.py       # exists
│   │   ├── research_watcher.py   # exists
│   │   ├── data_ingestion_watcher.py   # RENAME from dat-ingestion_watcher.py
│   │   └── (optional) needs_action_watcher.py   # watches only Needs_Action for user drops
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── db_handler.py         # Phase 1: Neon connect + basic queries (asyncpg)
│   │
│   ├── models/
│   │   └── drafts/               # Phase 2: Strategist output — Python strategy scripts (system-generated code)
│   │       └── .gitkeep
│   │
│   ├── agents/                   # Phase 2+: Librarian, Strategist, Monte Carlo, Regime, Risk
│   │   └── (future)
│   │
│   ├── mcp/                      # Phase 2+: data-mcp, trading-mcp, reporting-mcp
│   │   └── (future)
│   │
│   └── (optional)
│       ├── config.py             # paths, env, feature flags
│       └── orchestration/        # Ralph Wiggum loop, Orchestrator
│           └── (future)
│
├── specs.md
├── code_as_interface.md
├── claude_code_plan.md
├── IMPLEMENTATION_PLAN.md        # this file
├── requirements.txt
└── .env.example                  # ADD: VAULT_PATH, DATABASE_URL, etc. (no secrets)
```

### 4.3 Where “system codes, user reviews” lives

| User gives | System produces (code/instructions) | User reviews |
|------------|----------------------------------------|--------------|
| Prompt / research file | Research plan (e.g. `Plans/RESEARCH_PLAN_*.md`) | Read in `Plans/` or move to `Done` |
| Research plan | Python strategy in `src/models/drafts/*.py` | Optional review in repo; approval via HITL |
| Validated strategy / trade | Proposal in `Pending_Approval/` | Move to `Approved/` or `Rejected/` |

So: **implement the folder structure above** first; then add `db_handler.py`, then rename watcher and add `__init__.py`. That gives you a clear layout for “system writes code/plans → user reviews” without changing BaseWatcher behavior.

---

## 5. Implementation Order (for you)

1. **Create vault folders** under `AI_Employee_Vault/` as in §4.1 (and optional subdirs `Needs_Action/ResearchInput`, `Needs_Action/DataSource`).
2. **Create** `AI_Employee_Vault/Dashboard.md`, `Company_Handbook.md`, `Business_Goals.md` (can be stubs).
3. **Create** `src/db/` and `src/db/__init__.py`; implement `src/db/db_handler.py` (Neon + asyncpg, connect, basic read/write for `alphas` / `strategy_graveyard` / `market_regimes` / `agent_audit_logs`).
4. **Rename** `dat-ingestion_watcher.py` → `data_ingestion_watcher.py` and fix `type` in frontmatter; add `src/watchers/__init__.py`.
5. **Create** `src/models/drafts/` (e.g. with `.gitkeep`) for future strategy scripts.
6. **Add** `.env.example` and extend `requirements.txt` as you add agents/MCP (e.g. `pandas`, `numpy`, etc. per specs).

After that, Phase 2 (Monte Carlo, US30 loader, Ralph Wiggum loop) can follow the same layout; the “code-as-interface” flow (prompt → system codes → user reviews) is already supported by this structure.

---

## 6. Summary Table

| Item | Implemented | Action for you |
|------|-------------|----------------|
| BaseWatcher | Yes | None |
| ResearchWatcher | Yes | None |
| Data ingestion watcher | Yes (wrong name) | Rename + fix frontmatter |
| schema.sql | Yes | None |
| Vault folder structure | No | Create per §4.1 |
| db_handler.py | No | Add under `src/db/` |
| watchers `__init__.py` | No | Add |
| `src/models/drafts/` | No | Create |
| Code-as-interface layout | — | Use §4.1 + §4.2 so system-generated code/plans and HITL have clear places |

---

*End of implementation plan. You can implement the folder structure and the listed file renames/additions yourself using this document.*
