-- schema.sql
-- =============================================================================
-- AUTONOMOUS ALPHA RESEARCH & EXECUTION FTE - DATABASE SCHEMA
-- =============================================================================
-- This PostgreSQL schema stores all necessary data for the trading system:
-- - Validated trading strategies (alphas)
-- - Failed hypotheses for learning (strategy_graveyard)
-- - Metadata on market regimes for robust testing
-- - Audit logs of AI actions and decisions
-- =============================================================================

-- Alphas table: Stores validated strategy parameters and historical Sharpe ratios.
CREATE TABLE IF NOT EXISTS alphas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    parameters JSONB DEFAULT '{}',
    entry_logic TEXT,
    exit_logic TEXT,
    ideal_market_regime TEXT,
    sharpe_ratio DECIMAL(10,4),
    cagr DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    validation_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'validated', -- 'validated', 'live', 'retired'
    metadata JSONB DEFAULT '{}'
);

-- Strategy Graveyard: Stores failed hypotheses with reasons for failure.
CREATE TABLE IF NOT EXISTS strategy_graveyard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis TEXT NOT NULL,
    reason_for_failure TEXT,
    failed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    context JSONB DEFAULT '{}' -- e.g., market conditions, data used
);

-- Market Regimes: Metadata on US30 historical periods for cross-regime testing.
CREATE TABLE IF NOT EXISTS market_regimes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    description TEXT,
    characteristics JSONB DEFAULT '{}' -- e.g., volatility, trend
);

-- Agent Audit Logs: Tracks all actions, decisions, and outcomes of the AI agents.
CREATE TABLE IF NOT EXISTS agent_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_name VARCHAR(100) NOT NULL,
    action_type VARCHAR(100) NOT NULL, -- e.g., 'research_ingestion', 'hypothesis_extraction', 'strategy_generation', 'simulation_run', 'trade_proposal'
    action_details JSONB DEFAULT '{}',
    result VARCHAR(50), -- 'success', 'failure', 'pending_approval'
    human_approved BOOLEAN DEFAULT FALSE,
    approval_details JSONB DEFAULT '{}',
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_alphas_name ON alphas(name);
CREATE INDEX IF NOT EXISTS idx_strategy_graveyard_failed_at ON strategy_graveyard(failed_at);
CREATE INDEX IF NOT EXISTS idx_market_regimes_dates ON market_regimes(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_agent_audit_logs_timestamp ON agent_audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_agent_audit_logs_agent_action ON agent_audit_logs(agent_name, action_type);
