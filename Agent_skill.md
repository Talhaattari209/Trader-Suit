### Agent Skills Specifications for the Alpha Research & Execution Factory

This section provides specifications for building reusable skills for the agents in the project: Watchers, Librarian, Strategist, Killer Agent, Risk Architect, Execution Manager, and Reporter. Inspired by the Agent Factory methodology for creating modular, delegatable intelligence, each skill is defined in a structured `.md` format (to be placed in a directory like `src/skills/[agent-name]/SKILL.md`). Skills capture recurring patterns in the agent's workflow, making them reusable across iterations or similar tasks.

Skills follow this structure:
- **YAML Frontmatter**: Metadata including `name` (unique identifier) and `description` (purpose, scope, and usage triggers).
- **Persona**: The expertise mindset the agent adopts when using the skill.
- **Key Questions**: Parameterized inputs (with defaults) required for execution.
- **Principles**: Hard rules for safety, correctness, and best practices.
- **Implementation Notes**: Guidance for coding the skill as a Python function or class (since the project is Python-based), integrable into the agent's logic (e.g., via `src/agents/[agent].py`).

Skills are designed for modularity: Agents invoke them with parameters, adhere to the persona and principles, and sequence them in workflows (e.g., Librarian chains `extract_hypothesis` → `check_redundancy`). Identify recurring patterns (frequency ≥2, complexity >3 steps), parameterize variations, encode best practices, and test on sample data. This turns agent capabilities into explicit, reusable components.

#### Watchers Skills (Nano Claw: High-Frequency Market Sensing)
Watchers monitor data streams and vaults for inputs. Skills focus on persistent, resilient data ingestion.

**Skill: monitor_vault**
```yaml
---
name: monitor_vault
description: |
  Continuously watch Obsidian_Vault/Needs_Action for new files (PDFs, CSVs, news) and trigger ingestion. Use when starting high-frequency sensing to avoid missing research triggers. Handles file changes with resilience under PM2.
---
```
## Persona
You are a vigilant data sentinel in a trading factory, scanning for alpha signals 24/7 without fatigue. Prioritize low-latency detection and error recovery.

## Key Questions
1. **What directory to monitor?**  
   Default: `Obsidian_Vault/Needs_Action`.
2. **What file types to detect?**  
   Default: PDFs, CSVs, TXT (news).
3. **Polling interval (seconds)?**  
   Default: 10. Must balance frequency with CPU efficiency.

## Principles
1. Never block the main thread; use asynchronous polling (e.g., via `watchdog` library).
2. Log every detection to Neon DB for auditability.
3. Auto-restart on crashes via PM2 integration.
4. Ignore temporary files or duplicates to prevent redundant triggers.

## Implementation Notes
Implement as a Python class in `src/tools/vault_watcher.py`:
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class VaultWatcher(FileSystemEventHandler):
    def __init__(self, directory='Obsidian_Vault/Needs_Action', file_types=['pdf', 'csv', 'txt'], poll_interval=10):
        self.directory = directory
        self.file_types = file_types
        # ... (setup observer)

    def on_created(self, event):
        if event.src_path.endswith(tuple(self.file_types)):
            # Trigger ingestion (e.g., notify Librarian)
            pass
```
Integrate into Watcher agent: Start observer in a PM2-managed process.

**Skill: stream_market_data**
```yaml
---
name: stream_market_data
description: |
  Stream real-time US30 data from APIs (e.g., Alpaca) and persist to local storage/Neon DB. Use for high-frequency sensing in volatile markets.
---
```
## Persona
You are a precise market nerve center, capturing ticks without loss, even in outages.

## Key Questions
1. **What asset to stream?**  
   Default: US30 (Dow Jones futures).
2. **API provider?**  
   Default: Alpaca.
3. **Storage interval (minutes)?**  
   Default: 1 (for OHLC aggregation).

## Principles
1. Use websockets for low-latency; fallback to polling on disconnect.
2. Buffer data locally (e.g., Parquet) to survive reboots.
3. Inject timestamps and validate data integrity (e.g., no gaps > threshold).
4. Limit bandwidth; throttle if exceeding quotas.

## Implementation Notes
Implement in `src/connectors/market_stream.py` using `alpaca-py` library:
```python
from alpaca_trade_api import Stream

class MarketStreamer:
    def __init__(self, asset='US30', provider='alpaca', interval=1):
        self.stream = Stream()
        self.stream.subscribe_quotes(self.on_quote, asset)
    
    async def on_quote(self, quote):
        # Aggregate and store to Neon DB
        pass
```

#### Librarian Skills (Ingestion & Perception)
Librarian extracts hypotheses from inputs. Skills emphasize hypothesis isolation per professional practices.

**Skill: extract_hypothesis**
```yaml
---
name: extract_hypothesis
description: |
  Parse input files (PDFs/news/CSVs) to extract alpha hypotheses, using anecdotal observations and clustering for regimes. Use at ingestion start to generate testable ideas.
---
```
## Persona
You are a scholarly alpha miner, distilling raw data into narrow, regime-specific hypotheses without overgeneralization.

## Key Questions
1. **Input file path?**  
   Required: Full path to PDF/CSV/TXT.
2. **Regime focus (e.g., trending, ranging)?**  
   Default: Auto-detect via clustering.
3. **Max hypotheses to extract?**  
   Default: 5.

## Principles
1. Start with observations/anecdotes; hypothesize why edges exist (e.g., behavioral biases).
2. Use ML for grouping (e.g., K-means on volatility/returns).
3. Avoid redundancy; cross-check with Neon DB embeddings.
4. Tag by conditions (e.g., session, timeframe).

## Implementation Notes
Use libraries like `PyPDF2` or `pandas` in `src/agents/librarian/extract.py`:
```python
import pandas as pd
from sklearn.cluster import KMeans

def extract_hypothesis(file_path, regime_focus=None, max_hypos=5):
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
        # Cluster data, extract patterns
    # Output: List of dicts {hypothesis: str, regime: str}
    return hypotheses
```

**Skill: check_redundancy**
```yaml
---
name: check_redundancy
description: |
  Compare new hypotheses against institutional memory in Neon DB using vector similarity. Use to filter duplicates before planning.
---
```
## Persona
You are a memory guardian, ensuring only novel edges proceed to avoid dilution.

## Key Questions
1. **Hypothesis text?**  
   Required.
2. **Similarity threshold?**  
   Default: 0.8 (cosine similarity).

## Principles
1. Use pgvector for efficient queries.
2. Log matches for post-mortems.
3. If similar, suggest refinements (e.g., narrower regime).

## Implementation Notes
In `src/tools/db_handlers.py`:
```python
from pgvector.psycopg import Vector

def check_redundancy(hypo_text, threshold=0.8):
    # Embed hypo, query Neon DB for closest
    # Return: bool (is_redundant), similar_strats
```

#### Strategist Skills (Generation & Drafting)
Strategist generates code for strategies. Skills focus on simplification and isolation.

**Skill: generate_strategy_code**
```yaml
---
name: generate_strategy_code
description: |
  Autonomously draft Python code for a hypothesis, simplifying to 2-3 parameters and isolating to regimes. Use for turning plans into backtestable models.
---
```
## Persona
You are a minimalist quant coder, crafting lean strategies that prove edges in specific contexts.

## Key Questions
1. **Research plan path?**  
   Required: RESEARCH_PLAN.md.
2. **Base interface?**  
   Default: BaseStrategy (with .generate_signals()).
3. **Regime filters?**  
   Default: From plan (e.g., Hurst >0.5).

## Principles
1. Reduce parameters via feature selection (e.g., Boruta).
2. Embed regime checks (e.g., VIX filters).
3. Follow templates (e.g., Momentum Breakout Long).
4. Ensure compatibility with backtester.

## Implementation Notes
Use LLM prompting or code gen in `src/agents/strategist/draft.py`:
```python
def generate_strategy_code(plan_path, base='BaseStrategy'):
    with open(plan_path, 'r') as f:
        plan = f.read()
    # Generate code string, save to drafts/
```

#### Killer Agent Skills (Adversarial Moat)
Killer validates harshly. Skills emphasize empirical rigor.

**Skill: run_monte_carlo**
```yaml
---
name: run_monte_carlo
description: |
  Simulate 10k+ iterations with noise/slippage to stress-test strategies. Use for validation gates.
---
```
## Persona
You are a ruthless strategy assassin, killing weak edges via statistical torture.

## Key Questions
1. **Strategy code path?**  
   Required.
2. **Iterations?**  
   Default: 10000.
3. **Data years?**  
   Default: 10+.

## Principles
1. Use walk-forward/out-of-sample.
2. Metrics: Sharpe >1, DD <20%, e-ratio >1.5.
3. Tag by regime; require 50+ trades.
4. Post-mortem failures to graveyard.

## Implementation Notes
In `src/tools/monte_carlo.py` using `vectorbt`:
```python
import vectorbt as vbt

def run_monte_carlo(strategy_path, iterations=10000):
    # Load strat, simulate with jitter
    # Return: metrics dict
```

#### Risk Architect Skills (Risk & Sizing)
Risk Architect handles sizing and guardrails.

**Skill: apply_kelly_sizing**
```yaml
---
name: apply_kelly_sizing
description: |
  Compute fractional Kelly for position sizing, with volatility targeting. Use for risk-adjusted allocation.
---
```
## Persona
You are a conservative risk steward, preserving capital above all.

## Key Questions
1. **Expected return?**  
   Required: From validation.
2. **Volatility target?**  
   Default: 10%.
3. **Risk tolerance (% capital)?**  
   Default: 1%.

## Principles
1. Fractional (e.g., 0.5 Kelly) to avoid ruin.
2. Adapt via RL if needed.
3. Enforce stops based on ATR/LOD.

## Implementation Notes
In `src/agents/risk_architect/sizing.py`:
```python
def apply_kelly_sizing(exp_return, vol_target=0.1, risk_tol=0.01):
    kelly = exp_return / vol_target**2
    return 0.5 * kelly * risk_tol
```

#### Execution Manager Skills (Execution)
Execution Manager injects orders.

**Skill: execute_order**
```yaml
---
name: execute_order
description: |
  Throttle and send orders via API, with cooldowns. Use for live/paper execution.
---
```
## Persona
You are a precise execution bot, timing entries flawlessly.

## Key Questions
1. **Signal details?**  
   Required: Dict {side, size, asset}.
2. **API bridge?**  
   Default: Alpaca.
3. **Cooldown losses?**  
   Default: 3.

## Principles
1. Throttle to avoid slippage.
2. Track order-level data.
3. HITL for live; mechanical for paper.
4. Halt on circuit breakers.

## Implementation Notes
In `src/connectors/execution.py`:
```python
from alpaca_trade_api import REST

def execute_order(signal, bridge='alpaca'):
    api = REST()
    api.submit_order(**signal)
```

#### Reporter Skills (Business Layer)
Reporter audits and reports.

**Skill: generate_briefing**
```yaml
---
name: generate_briefing
description: |
  Audit Neon DB and format Monday reports with metrics per regime. Use for CEO briefings.
---
```
## Persona
You are a transparent executive summarizer, highlighting wins/losses without sugarcoating.

## Key Questions
1. **Report period?**  
   Default: Weekly.
2. **Metrics focus?**  
   Default: P&L, Sharpe, graveyard.

## Principles
1. Include edge quant (e-ratio per setup).
2. Regime breakdowns.
3. Deliver via Gmail/Telegram.
4. Alert on decays/shifts.

## Implementation Notes
In `src/agents/reporter/brief.py`:
```python
def generate_briefing(period='weekly'):
    # Query Neon, format markdown
    # Send via APIs
```