For a professional-grade **Actor-Critic** workflow in Alpha research, you aren't just building a "bot"—you are building a **Generative Quant Lab**. In this architecture, the **Actor** is the "Alpha Hunter" (generating hypotheses and entry/exit logic), and the **Critic** is the "Adversarial Risk Manager" (trying to break the strategy).

Here are the detailed specs for your **Coding Agent**.

### 1. The Actor Agent: The "Alpha Hunter"

The Actor's goal is to find non-linear relationships in your US30 data and propose executable strategies.

* **Primary Model: PPO (Proximal Policy Optimization)**
* **Why:** PPO is the industry standard for trading because it is stable and handles the "non-stationary" (constantly changing) nature of financial markets better than DQN.


* **Architecture: Transformer-based Encoder**
* Professional quants use **Attention Mechanisms** to weight different look-back periods. Instead of a simple LSTM, a Transformer-head allows the Actor to "pay attention" to specific volatility spikes or session opens (like the NY open for US30).


* **Action Space:** **Continuous Action Control.**
* Instead of just "Buy/Sell," the Actor should output a value between -1 and 1, representing the **conviction level** (position size).



### 2. The Critic Agent: The "Adversarial Stress-Tester"

The Critic’s job is to ensure the Actor isn't just "curve-fitting" (memorizing the past).

* **Primary Model: Multi-Headed Value Network**
* The Critic doesn't just estimate "Profit." It has separate heads for **Expected Return**, **Maximum Drawdown (MDD)**, and **Value at Risk (VaR)**.


* **Validation Method: Synthetic Noise Injection (Adversarial Machine Learning)**
* The Critic should inject "jitter" into your US30 OHLCV data—shifting prices by 1-2 pips or shuffling volume—to see if the Actor's strategy collapses. If the strategy fails under noise, the Critic "kills" the strategy.


* **Monte Carlo Integration:**
* The Critic runs **10,000+ permutations** of the trade sequence to calculate the "Probability of Ruin."



---

### 3. Technical Specs for the Coding Agent (`specs.md` extension)

Copy this specific logic into your `specs.md` to guide the implementation:

```markdown
## Specialized Actor-Critic Implementation Specs

### A. Environment (The Gym)
- **Reward Function**: Not just P&L. Use a **Risk-Adjusted Reward** (Sharpe Ratio * Sortino Ratio) to punish the Actor for high-volatility "gambling."
- **State Space**: Include OHLCV, RSI, ATR (Volatility), and Time-of-Day (US30 specific session logic).

### B. Actor Neural Network
- **Input Layer**: 1D Convolutional Neural Network (CNN) for local pattern recognition (e.g., candlestick patterns).
- **Hidden Layer**: Transformer Encoder block to handle long-range dependencies in US30 price cycles.
- **Output Layer**: Tanh activation for continuous position sizing (-1 to +1).

### C. Critic Neural Network
- **Input Layer**: Shares the same CNN/Transformer features as the Actor (Shared Representation).
- **Evaluation Logic**: Use **Temporal Difference (TD) Error** to judge if the Actor's current trade path is better than the average "Buy & Hold" or "Random Walk."

### D. The "Validation Moat" Pipeline
1. **Actor** proposes a strategy signal.
2. **Critic** runs a "Noise Stress Test" (Random Pip Jitter).
3. **Critic** runs a "Liquidity Stress Test" (Simulated 2-3 pip slippage).
4. **Final Check**: Only if the "Probability of Profit" remains > 60% across 5,000 Monte Carlo iterations does the strategy move to `Obsidian_Vault/Done`.

```

---

### 4. Comparison for Decision Making

| Model Type | Best For | Role in Your FTE |
| --- | --- | --- |
| **PPO (RL)** | Continuous decision making | **The Actor** (Strategic execution) |
| **LSTM (DL)** | Time-series forecasting | **The Perception Layer** (Predicting next hour) |
| **Random Forest (ML)** | Feature importance | **The Critic** (Identifying why a trade failed) |
| **Transformer** | Complex pattern recognition | **The Brain** (Processing 10 years of US30 data) |

---

# Database Environment
This PostgreSQL initialization script is designed for your Neon DB to serve as the long-term "Institutional Memory" for the US30 Alpha Research project. It utilizes **UUIDs** for future-proofing and **JSONB** for flexible strategy parameters, ensuring the schema remains robust for a multi-year lifecycle.

### Neon DB Initialization Script

Run the following commands in the **Neon SQL Editor** to set up your tables:

```sql
-- Enable the pgvector extension for similarity searches on strategy hypotheses
CREATE EXTENSION IF NOT EXISTS vector;

-- Table: Alphas (Successful strategies)
CREATE TABLE IF NOT EXISTS alphas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name VARCHAR(255) NOT NULL,
    hypothesis_text TEXT,
    embedding VECTOR(1536), -- For search/comparison of similar ideas
    parameters JSONB NOT NULL, -- Flexible storage for indicators, timeframes, etc.
    performance_metrics JSONB, -- Sharpe, Sortino, Drawdown history
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'active'
);

-- Table: Strategy Graveyard (Failed or decayed strategies)
CREATE TABLE IF NOT EXISTS strategy_graveyard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_alpha_id UUID REFERENCES alphas(id),
    strategy_name VARCHAR(255),
    failure_reason TEXT NOT NULL,
    last_known_metrics JSONB,
    killed_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB -- Context like "Killed during 2026 CPI volatility"
);

-- Table: Backtest Logs (Detailed trace of every simulation)
CREATE TABLE IF NOT EXISTS backtest_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alpha_id UUID REFERENCES alphas(id),
    regime_type VARCHAR(100), -- e.g., 'high_volatility', 'sideways'
    monte_carlo_p_value FLOAT,
    slippage_simulated FLOAT,
    is_robust BOOLEAN,
    log_data TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table: Market Regimes (Reference for the Critic agent)
CREATE TABLE IF NOT EXISTS market_regimes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100),
    start_date DATE,
    end_date DATE,
    description TEXT,
    volatility_profile VARCHAR(50) -- 'Low', 'Medium', 'Extreme'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_alphas_status ON alphas(status);
CREATE INDEX IF NOT EXISTS idx_backtest_alpha_id ON backtest_logs(alpha_id);

```

### Next Implementation Steps

With the database initialized, you can now direct **Claude Code** to link the Python logic to these tables:

1. **Environment Sync**: Ensure your `.env` file contains the `NEON_DATABASE_URL`.
2. **The Database Handler**: Ask Claude to generate the `src/tools/db_handler.py` using `asyncpg` to perform **upserts** into the `alphas` table and **logging** into `backtest_logs`.
3. **The Librarian Update**: Configure the **Librarian Agent** to first query the `alphas` and `strategy_graveyard` tables using a similarity search (vector) before starting a new research task to avoid redundant work.
