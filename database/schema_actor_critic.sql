-- schema_actor_critic.sql
-- =============================================================================
-- ACTOR-CRITIC EXTENSION TO BASE SCHEMA
-- =============================================================================
-- Run this after database/schema.sql to add:
--   - pgvector for strategy/hypothesis similarity search (Librarian, alphas)
--   - backtest_logs for Critic/Killer Agent simulation traces
--   - Optional columns on alphas and market_regimes for Actor-Critic use
-- =============================================================================

-- Enable similarity search on strategy hypotheses (Neon supports pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Backtest Logs: detailed trace of every Critic/Killer simulation
CREATE TABLE IF NOT EXISTS backtest_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alpha_id UUID REFERENCES alphas(id),
    regime_type VARCHAR(100),       -- e.g. 'high_volatility', 'sideways'
    monte_carlo_p_value FLOAT,
    slippage_simulated FLOAT,
    is_robust BOOLEAN,
    log_data TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_alpha_id ON backtest_logs(alpha_id);
CREATE INDEX IF NOT EXISTS idx_backtest_created ON backtest_logs(created_at);

-- Optional: embedding on alphas for Librarian similarity search (avoids redundant research)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'alphas' AND column_name = 'embedding'
    ) THEN
        ALTER TABLE alphas ADD COLUMN embedding vector(1536);
    END IF;
END $$;

-- Optional: volatility_profile on market_regimes for Critic reference
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'market_regimes' AND column_name = 'volatility_profile'
    ) THEN
        ALTER TABLE market_regimes ADD COLUMN volatility_profile VARCHAR(50);
    END IF;
END $$;
