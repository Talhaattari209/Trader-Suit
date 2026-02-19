# Actor-Critic Models: Generative Quant Lab

This document is the canonical reference for the **Actor-Critic** workflow embedded in the Alpha Research FTE. It is derived from `Actor_critic_models.md`.

## Vision

For a professional-grade Actor-Critic workflow you are building a **Generative Quant Lab**. The **Actor** is the "Alpha Hunter" (hypotheses and entry/exit logic); the **Critic** is the "Adversarial Risk Manager" (stress-testing and killing weak strategies).

---

## 1. The Actor Agent: The "Alpha Hunter"

The Actor finds non-linear relationships in US30 data and proposes executable strategies.

- **Primary Model:** PPO (Proximal Policy Optimization) — stable for non-stationary markets; preferred over DQN for trading.
- **Architecture:** Transformer-based Encoder with attention over look-back periods (e.g. volatility spikes, NY open).
- **Action Space:** Continuous control: output in **[-1, 1]** as **conviction level** (position size), not just Buy/Sell.

---

## 2. The Critic Agent: The "Adversarial Stress-Tester"

The Critic ensures the Actor is not curve-fitting.

- **Primary Model:** Multi-headed value network — separate heads for **Expected Return**, **MDD**, and **VaR**.
- **Validation:** Synthetic noise injection (pip jitter, volume shuffle) on US30 OHLCV; kill strategies that collapse under noise.
- **Monte Carlo:** 10,000+ permutations to compute **Probability of Ruin**.

---

## 3. Technical Implementation Specs

### A. Environment (The Gym)

- **Reward:** Risk-adjusted (e.g. Sharpe × Sortino), not raw P&L.
- **State:** OHLCV, RSI, ATR, Time-of-Day (US30 session logic).

### B. Actor Neural Network

- **Input:** 1D CNN for local patterns (e.g. candlestick).
- **Hidden:** Transformer Encoder for long-range dependencies.
- **Output:** Tanh for continuous position size (-1 to +1).

### C. Critic Neural Network

- **Input:** Shared CNN/Transformer representation with Actor.
- **Evaluation:** TD (Temporal Difference) error vs. Buy & Hold / Random Walk.

### D. Validation Moat Pipeline

1. **Actor** proposes a strategy signal.
2. **Critic** runs **Noise Stress Test** (random pip jitter).
3. **Critic** runs **Liquidity Stress Test** (2–3 pip slippage).
4. **Gate:** Strategy moves to `Obsidian_Vault/Done` only if **Probability of Profit** > 60% over 5,000 Monte Carlo iterations.

---

## 4. Model Roles in the FTE

| Model Type       | Best For                 | Role in FTE                          |
|------------------|--------------------------|--------------------------------------|
| **PPO (RL)**     | Continuous decisions     | **Actor** (strategic execution)      |
| **LSTM (DL)**    | Time-series forecasting  | **Perception layer** (e.g. next hour)|
| **Random Forest**| Feature importance       | **Critic** (why a trade failed)      |
| **Transformer** | Complex pattern recognition | **Brain** (e.g. 10y US30 data)   |

---

## 5. Database (Neon): Institutional Memory

The project uses PostgreSQL (Neon) with **UUIDs** and **JSONB** for strategy parameters. For Actor-Critic and similarity search:

- **pgvector** is used for strategy/hypothesis embeddings.
- **backtest_logs** stores each simulation (regime, Monte Carlo p-value, slippage, robustness).
- **Librarian** should query `alphas` and `strategy_graveyard` via similarity search before starting new research.

### Schema Additions

- **New table:** `backtest_logs` — see `database/schema_actor_critic.sql`.
- **Extensions:** `vector` (pgvector) for embeddings on `alphas`.
- **market_regimes:** optional `volatility_profile` for Critic reference.

Run `database/schema_actor_critic.sql` on an existing DB to add these. For a greenfield Neon DB, the full script in the next section can be used instead of or after `database/schema.sql`.

### Greenfield Neon DB Script (optional)

If you initialize a new Neon project and want the Actor-Critic–oriented schema (alphas with embeddings, backtest_logs, graveyard with `original_alpha_id`), run in the Neon SQL Editor:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS alphas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name VARCHAR(255) NOT NULL,
    hypothesis_text TEXT,
    embedding VECTOR(1536),
    parameters JSONB NOT NULL,
    performance_metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS strategy_graveyard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_alpha_id UUID REFERENCES alphas(id),
    strategy_name VARCHAR(255),
    failure_reason TEXT NOT NULL,
    last_known_metrics JSONB,
    killed_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS backtest_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alpha_id UUID REFERENCES alphas(id),
    regime_type VARCHAR(100),
    monte_carlo_p_value FLOAT,
    slippage_simulated FLOAT,
    is_robust BOOLEAN,
    log_data TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_regimes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100),
    start_date DATE,
    end_date DATE,
    description TEXT,
    volatility_profile VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_alphas_status ON alphas(status);
CREATE INDEX IF NOT EXISTS idx_backtest_alpha_id ON backtest_logs(alpha_id);
```

---

## 6. Implementation Checklist

1. **Environment:** `.env` includes `NEON_DATABASE_URL`.
2. **DB handler:** `src/db/db_handler.py` supports **upserts** to `alphas` and **inserts** to `backtest_logs` (see existing methods and any new ones in the codebase).
3. **Librarian:** Before new research, query `alphas` and `strategy_graveyard` (with vector similarity when embeddings exist) to avoid redundant work.
4. **Killer Agent / Critic:** Use `backtest_logs` to record each stress test (noise, slippage, Monte Carlo result) and only approve strategies that pass the Validation Moat (e.g. Prob. of Profit > 60%).

---

## 7. References

- **specs.md** — Section 7: Specialized Actor-Critic Implementation.
- **database/schema.sql** — Base schema; **database/schema_actor_critic.sql** — Actor-Critic additions.
- **Actor_critic_models.md** — Original source document.
