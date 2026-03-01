"""
Database handler for Neon PostgreSQL: alphas, strategy_graveyard, market_regimes,
agent_audit_logs, and (when schema_actor_critic is applied) backtest_logs.
See docs/ACTOR_CRITIC_SPECS.md for Actor-Critic schema and usage.
"""
import os
import asyncpg
import logging
from typing import List, Dict, Any, Optional
import json

class DBHandler:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
        self.logger = logging.getLogger(self.__class__.__name__)

    async def connect(self):
        """Establish a connection pool to the database."""
        try:
            self.pool = await asyncpg.create_pool(dsn=self.database_url)
            self.logger.info("Connected to database")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise

    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            self.logger.info("Database connection closed")

    async def fetch_alphas(self) -> List[Dict[str, Any]]:
        """Retrieve all alphas."""
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as connection:
            records = await connection.fetch("SELECT * FROM alphas")
            return [dict(record) for record in records]

    async def add_alpha(self, name: str, description: str, parameters: Dict, 
                       entry_logic: str, exit_logic: str, 
                       sharpe_ratio: float, cagr: float, max_drawdown: float):
        """Insert a new alpha strategy."""
        if not self.pool:
            await self.connect()
            
        query = """
            INSERT INTO alphas (name, description, parameters, entry_logic, exit_logic, 
                              sharpe_ratio, cagr, max_drawdown)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, name, description, json.dumps(parameters), 
                                           entry_logic, exit_logic, 
                                           sharpe_ratio, cagr, max_drawdown)

    async def log_agent_action(self, agent_name: str, action_type: str, 
                              action_details: Dict, result: str):
        """Log an agent's action."""
        if not self.pool:
            await self.connect()

        query = """
            INSERT INTO agent_audit_logs (agent_name, action_type, action_details, result)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, agent_name, action_type, json.dumps(action_details), result)

    async def add_to_graveyard(self, hypothesis: str, reason_for_failure: str, context: Dict = None):
        """Add a failed strategy to the graveyard."""
        if not self.pool:
            await self.connect()

        query = """
            INSERT INTO strategy_graveyard (hypothesis, reason_for_failure, context)
            VALUES ($1, $2, $3)
            RETURNING id
        """
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, hypothesis, reason_for_failure, json.dumps(context or {}))

    async def fetch_graveyard_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent graveyard entries for Reporter (Paradigms Task 1). context may include failure_mode, metrics_json."""
        if not self.pool:
            await self.connect()
        query = """
            SELECT id, hypothesis, reason_for_failure, context
            FROM strategy_graveyard
            ORDER BY id DESC
            LIMIT $1
        """
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(query, limit)
                return [
                    {
                        "id": r["id"],
                        "hypothesis": r["hypothesis"],
                        "reason_for_failure": r["reason_for_failure"],
                        "context": json.loads(r["context"]) if r.get("context") else {},
                    }
                    for r in rows
                ]
        except Exception as e:
            self.logger.warning("fetch_graveyard_entries: %s", e)
            return []

    async def fetch_market_regimes(self) -> List[Dict[str, Any]]:
        """Retrieve all market regimes."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as connection:
            records = await connection.fetch("SELECT * FROM market_regimes")
            return [dict(record) for record in records]

    # ---------- Actor-Critic / Killer Agent: backtest_logs (requires schema_actor_critic.sql) ----------

    async def log_backtest(
        self,
        alpha_id: str,
        regime_type: Optional[str] = None,
        monte_carlo_p_value: Optional[float] = None,
        slippage_simulated: Optional[float] = None,
        is_robust: Optional[bool] = None,
        log_data: Optional[str] = None,
    ) -> Optional[str]:
        """Insert a backtest log entry (Critic/Killer Agent stress test). Returns log id or None if table missing."""
        if not self.pool:
            await self.connect()
        query = """
            INSERT INTO backtest_logs (alpha_id, regime_type, monte_carlo_p_value, slippage_simulated, is_robust, log_data)
            VALUES ($1::uuid, $2, $3, $4, $5, $6)
            RETURNING id
        """
        try:
            async with self.pool.acquire() as connection:
                return await connection.fetchval(
                    query,
                    alpha_id,
                    regime_type,
                    monte_carlo_p_value,
                    slippage_simulated,
                    is_robust,
                    log_data,
                )
        except asyncpg.UndefinedTableError:
            self.logger.warning("backtest_logs table not found; run database/schema_actor_critic.sql")
            return None
