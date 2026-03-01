# Agent Operating Instructions

This file is injected into agent context at cycle start (OpenClaw-style bootstrap).

## Ralph Wiggum Loop

1. **Librarian**: Reads from `Needs_Action/`, produces structured RESEARCH_PLAN in `Plans/`. Extract alpha hypotheses; tag by regime; avoid redundancy via institutional memory.
2. **Strategist**: Reads from `Plans/`, writes strategy code to `src/models/drafts/`. Follow BaseStrategy interface; embed regime filters and market param hooks.
3. **Killer**: Validates drafts via Monte Carlo Pro. Pass → `src/models/production/`; fail → graveyard with journaled post-mortem.
4. **Risk Architect**: Sizing (e.g. fractional Kelly), guardrails, circuit breakers. Cooldown after N consecutive losses.
5. **Execution Manager**: Throttled execution; HITL for live (file move Plans → Approved).
6. **Reporter**: Monday briefings; graveyard summaries; Telegram/Gmail.

## Conventions

- All agents log to vault `Logs/` where applicable.
- High-leverage or live trades require manual approval (file in Approved/).
- Zero-MQL: execution logic in Python only.
