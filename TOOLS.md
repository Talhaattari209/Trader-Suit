# Tool Guidance

When to use which tools and safety rules (injected at cycle start).

## Tools by Agent

- **Librarian**: extract_hypothesis (PDF/CSV/TXT → hypotheses), check_redundancy (Neon/pgvector). Tag by regime; max 5 hypotheses per run unless specified.
- **Strategist**: generate_strategy_code (RESEARCH_PLAN → Python draft). Must follow BaseStrategy; include regime checks and optional market param hooks.
- **Killer**: run_monte_carlo (MCP). 10k+ iterations; noise/slippage; metrics Sharpe, DD, e-ratio. On failure, write journaled post-mortem to graveyard.
- **Risk Architect**: apply_kelly_sizing (fractional Kelly, vol target). Enforce circuit breaker after 3 consecutive losses.
- **Execution Manager**: execute_order (throttled). HITL for live; respect circuit breakers.
- **Reporter**: generate_briefing (Neon audit → Gmail/Telegram). Include graveyard summaries and alpha decay trends.

## Safety

- Never execute live orders without approval (Approved/).
- Never skip Monte Carlo validation for strategies promoted to production.
- Log all detections and decisions for auditability (Neon / Logs).
