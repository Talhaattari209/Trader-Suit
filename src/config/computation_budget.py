"""
Computation Budget — single source of truth for all heavy operation sample counts.

Set env var COMPUTE_PROFILE=local  (default)  → 80-90% reduced, fast local exploration
Set env var COMPUTE_PROFILE=colab             → full resolution, deep validation on T4

Every module that has a tunable sample count / iteration count imports:

    from src.config.computation_budget import budget as CB
    ...
    self.iterations = CB.mc_iterations
"""

import os
from dataclasses import dataclass

COMPUTE_PROFILE: str = os.environ.get("COMPUTE_PROFILE", "local").lower()


@dataclass(frozen=True)
class _Budget:
    # ── Monte Carlo ────────────────────────────────────────────────────────
    mc_iterations: int          # main simulation paths
    mc_nudges: int              # parameter stability nudges
    mc_regime_iters: int        # paths per regime stress test
    mc_indicator_samples: int   # TA param sweep samples per indicator

    # ── Data window ───────────────────────────────────────────────────────
    data_max_bars: int          # max 1H candles loaded for any computation
    backtest_bars: int          # bars used in backtest / signal generation
    price_level_lookback: int   # bars for liquidity zone / FVG detection

    # ── SHAP ─────────────────────────────────────────────────────────────
    shap_n_samples: int         # subsample size for SHAP explainer

    # ── Walk-forward ──────────────────────────────────────────────────────
    wf_n_folds: int             # walk-forward validation folds
    wf_train_pct: float         # fraction of each fold used for training

    # ── RL / DL ───────────────────────────────────────────────────────────
    rl_max_episodes: int        # max RL training episodes
    rl_replay_buffer_size: int  # experience replay buffer capacity
    rl_batch_size: int          # RL mini-batch size per gradient step
    rl_eval_freq: int           # evaluate every N episodes
    dl_epochs: int              # max DL training epochs
    dl_batch_size: int          # DL training batch size

    # ── Agent loop ────────────────────────────────────────────────────────
    agent_poll_interval_s: float  # seconds between vault watcher polls
    similarity_top_k: int         # top-K similar alphas to retrieve

    # ── UI / API ──────────────────────────────────────────────────────────
    chart_max_candles: int      # max candles shown in the trade chart
    activity_feed_limit: int    # rows in activity / audit log feed


_PROFILES: dict[str, _Budget] = {

    # ─────────────────────────────────────────────────────────────────────
    # LOCAL — fast exploration on Windows PC CPU
    # Target: every heavy operation completes in < 30 s
    # ─────────────────────────────────────────────────────────────────────
    "local": _Budget(
        # Monte Carlo
        mc_iterations         = 1_000,   # was 10,000  → 90% reduction
        mc_nudges             = 5,       # was 20      → 75% reduction
        mc_regime_iters       = 300,     # was 3,000   → 90% reduction
        mc_indicator_samples  = 5,       # was 20      → 75% reduction
        # Data
        data_max_bars         = 500,     # caps data I/O and resampling
        backtest_bars         = 300,     # focused 12-day signal window
        price_level_lookback  = 100,     # last 100 1H bars covers active levels
        # SHAP
        shap_n_samples        = 20,      # was 100 → 80% reduction; stable above 15
        # Walk-forward
        wf_n_folds            = 3,       # was 5 → 40% reduction
        wf_train_pct          = 0.80,
        # RL
        rl_max_episodes       = 200,     # was 2,000 → 90% reduction
        rl_replay_buffer_size = 5_000,   # fits in <100MB RAM
        rl_batch_size         = 32,
        rl_eval_freq          = 50,
        # DL
        dl_epochs             = 10,      # EarlyStopping(patience=3) triggers early
        dl_batch_size         = 32,
        # Agent
        agent_poll_interval_s = 5.0,    # reduces background CPU spin
        similarity_top_k      = 3,
        # UI
        chart_max_candles     = 150,     # Plotly renders in ~50ms vs 200ms at 500
        activity_feed_limit   = 10,
    ),

    # ─────────────────────────────────────────────────────────────────────
    # COLAB — full deep validation on T4 GPU (no reductions)
    # ─────────────────────────────────────────────────────────────────────
    "colab": _Budget(
        mc_iterations         = 10_000,
        mc_nudges             = 20,
        mc_regime_iters       = 3_000,
        mc_indicator_samples  = 20,

        data_max_bars         = 5_000,
        backtest_bars         = 2_000,
        price_level_lookback  = 500,

        shap_n_samples        = 100,

        wf_n_folds            = 5,
        wf_train_pct          = 0.80,

        rl_max_episodes       = 2_000,
        rl_replay_buffer_size = 50_000,
        rl_batch_size         = 128,
        rl_eval_freq          = 200,
        dl_epochs             = 100,
        dl_batch_size         = 256,

        agent_poll_interval_s = 2.0,
        similarity_top_k      = 5,

        chart_max_candles     = 500,
        activity_feed_limit   = 50,
    ),
}


def get() -> _Budget:
    """Return the active ComputationBudget for the current COMPUTE_PROFILE."""
    profile = COMPUTE_PROFILE
    if profile not in _PROFILES:
        print(f"[ComputationBudget] Unknown profile '{profile}', falling back to 'local'")
        profile = "local"
    return _PROFILES[profile]


# Module-level singleton — import this for convenience
budget: _Budget = get()
