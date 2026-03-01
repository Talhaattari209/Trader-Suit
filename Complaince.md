The **Alpha Research & Execution Factory Compliance Document**  
**Version 1.0**  
**Date**: February 22, 2026  
**Project Scope**: Autonomous AI-driven trading research and execution system for US30 (Dow Jones futures/index), using agents (Watchers, Librarian, Strategist, Killer Agent, Risk Architect, Execution Manager, Reporter) in a modular Python-based architecture with OpenClaw (proactive reasoning) and NanoClaw (resilient execution).  
**Deployment Context**: Hybrid local/GCP setup; primarily paper trading or personal/educational use initially, with potential live execution via Alpaca API or MT5 bridge. Human-in-the-Loop (HITL) required for live trades.

This document outlines compliance obligations, controls, best practices, and safeguards for the project. It draws from key U.S. regulations (SEC, FINRA, CFTC), international standards (MiFID II RTS 6), and industry best practices for algorithmic/automated trading systems as of 2026. Even for non-registered personal or research use, these principles reduce legal, operational, and market risks.

### 1. Regulatory Framework & Applicability (2026 Context)
- **U.S. (Primary Jurisdiction Assumed)**  
  - **SEC Rule 15c3-5** (Market Access Rule): Requires robust pre-trade risk controls (e.g., order size, credit limits, fat-finger prevention) for broker-dealers providing market access. Applies if using a broker API for live execution.  
  - **FINRA Rules** — 3110 (Supervision), 5210 (Publication of Transactions), 204-2 (Recordkeeping), 206(3)-1 (Marketing). Guidance from Regulatory Notice 15-09: Effective supervision for algorithmic strategies.  
  - **CFTC** (for futures like US30): Risk controls, system safeguards, pre-trade limits.  
  - 2025–2026 Priorities: Enhanced focus on algorithmic/AI trading oversight, system integrity, data governance, black-box risks, and stress testing. FINRA/SEC emphasize audit trails, kill switches, and active supervision.

- **International (MiFID II / RTS 6 — If EU Exposure or Best Practice)**  
  - Article 17: Effective systems/risk controls for resilience, capacity, thresholds/limits, prevention of erroneous orders/market disorder, business continuity, annual self-assessment. Notification to authorities if algorithmic trading occurs.

- **Project Status**  
  - Not a registered broker-dealer/investment adviser (assumed personal/research use).  
  - No public solicitation/marketing of strategies.  
  - Live execution requires broker compliance (Alpaca/MT5 terms) + personal account rules.  
  - If scaled to managed accounts/funds → full registration + ADV disclosures needed.

### 2. Core Compliance Principles Embedded in the Project
1. **Human-in-the-Loop (HITL) & Supervision**  
   - All live trades require manual approval (file move from /Plans → /Approved in Obsidian_Vault).  
   - No fully autonomous live execution without explicit human sign-off.  
   - Telegram commands (/pause, /approve) for emergency halt and oversight.

2. **Risk Controls & System Safeguards**  
   - Pre-trade: Fractional Kelly + volatility targeting; order throttling; max position/size limits.  
   - Post-trade: Cooldown after 3 losses; circuit breakers on drawdown/vol spikes.  
   - Kill switch: Immediate halt via Telegram /pause or PM2 stop.  
   - Stress testing: Monte Carlo (10k+ iterations) with synthetic noise (1-2 pip jitter), slippage (2-3 pip), regime shocks.  
   - Resilience: PM2 auto-restart; state persistence to Neon DB every 60s; segregated dev/test/prod.

3. **Testing & Validation**  
   - Killer Agent adversarial moat: Walk-forward, out-of-sample, regime-tagged backtests (10+ years data).  
   - Metrics gates: Sharpe >1, DD <20%, e-ratio >1.5, 50+ trades min.  
   - Annual self-assessment equivalent: Quarterly Reporter audits + graveyard post-mortems.

4. **Recordkeeping & Audit Trails**  
   - Neon DB (PostgreSQL + pgvector): Logs every hypothesis, strategy version, backtest metrics, approval decisions, execution signals, P&L.  
   - Retain 5+ years (aligns with SEC Rule 204-2).  
   - Immutable logs: Timestamped entries; vector embeddings for similarity checks.  
   - Graveyard: Failure modes, regime decays, post-mortems.

5. **Market Integrity & Abuse Prevention**  
   - No spoofing/layering/self-trades (guard via throttled execution + monitoring).  
   - Regime isolation avoids overgeneralization/overfitting.  
   - Narrow setups only (e.g., session-specific, Hurst-tagged) to prevent manipulation-like behavior.

6. **Data & Security**  
   - API keys in .env (never committed).  
   - Limited entitlements: Execution Manager has throttled access.  
   - No direct live keys without HITL.  
   - Cybersecurity: Local GPU for heavy compute; GCP free tier for monitoring.

7. **Reporting & Transparency**  
   - Monday CEO Briefing: P&L, Sharpe, signal decay, graveyard, regime performance.  
   - Telegram alerts for breaches/cooldowns.  
   - No public performance claims without disclaimers.

### 3. Agent-Specific Compliance Responsibilities
- **Watchers** — Accurate data ingestion; no manipulation of feeds; log anomalies.  
- **Librarian** — Hypothesis extraction without fabrication; redundancy checks via embeddings.  
- **Strategist** — Code simplification (2-3 params); regime tagging; BaseStrategy compliance.  
- **Killer Agent** — Rigorous, unbiased validation; document failures.  
- **Risk Architect** — Conservative sizing (0.5 Kelly); adaptive RL with guardrails.  
- **Execution Manager** — Throttled, logged orders; cooldown enforcement; slippage tracking.  
- **Reporter** — Accurate metrics; no misleading summaries.

### 4. Risk Register & Mitigation
| Risk | Likelihood (2026) | Impact | Mitigation |
|------|-------------------|--------|------------|
| Erroneous orders / flash crash contribution | Medium | High | Pre-trade limits, noise/slippage stress, kill switch |
| Overfitting / curve-fitting death | High | High | Adversarial moat, walk-forward, regime isolation |
| Data feed outage → bad decisions | Medium | Medium | PM2 restart, multi-provider failover (future) |
| Live execution without approval | Low | Critical | Strict HITL gate; no auto-live |
| Regulatory scrutiny if live-scaled | Low-Medium | High | Start paper; document everything |
| Black-box AI opacity | Medium | High | Versioned code, logs, post-mortems |

### 5. Ongoing Obligations & Review
- **Quarterly Review** — Re-assess controls, retrain RL if needed, update graveyard.  
- **Annual Equivalent** — Full self-assessment against this doc + regulatory updates.  
- **Updates** — Monitor SEC/FINRA/CFTC priorities (AI/algo focus in 2026).  
- **If Live Trading Begins** — Consult legal counsel; ensure broker (Alpaca/etc.) compliance; consider Series 57 if developing algos professionally.

### 6. Disclaimer & Sign-Off
This system is designed for research, backtesting, and personal paper trading. Live trading involves substantial risk of loss and is not suitable for all. No strategy is guaranteed. The project owner assumes full responsibility for use.

**Approved by Project Owner** _______________________ Date: __________

This document serves as the master compliance blueprint. Store in Obsidian_Vault/Reports/Compliance.md and reference in every major release. Update on material changes (e.g., live go-live, new agents).