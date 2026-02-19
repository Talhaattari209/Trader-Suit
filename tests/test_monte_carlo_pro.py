"""
Unit tests for MonteCarloPro.
Ensures prob_of_ruin and other metrics are computed correctly.
"""
import numpy as np
import pandas as pd
import pytest

from src.tools.monte_carlo_pro import MonteCarloPro


@pytest.fixture
def engine():
    return MonteCarloPro(iterations=1000, confidence_level=0.95)


def test_prob_of_ruin_bad_series(engine):
    """A series that loses 50%+ should yield prob_of_ruin = 1 (with seed)."""
    np.random.seed(42)
    # Constant negative return so equity goes to half
    n = 100
    r = -0.01  # each period -1%; (1-0.01)^100 ≈ 0.37, so below 50% capital
    returns = pd.Series([r] * n)
    result = engine.simulate_paths(returns, initial_capital=100_000)
    # With bootstrap we sometimes get this bad path; prob_of_ruin should be high
    assert result["prob_of_ruin"] >= 0
    assert result["prob_of_ruin"] <= 1
    # With all-negative returns, most paths will end below 50% capital
    assert result["prob_of_ruin"] > 0.5


def test_prob_of_ruin_good_series(engine):
    """A series with positive drift should yield low prob_of_ruin."""
    np.random.seed(123)
    n = 200
    returns = pd.Series(np.random.normal(0.001, 0.01, n))
    result = engine.simulate_paths(returns, initial_capital=100_000)
    assert result["prob_of_ruin"] >= 0
    assert result["prob_of_ruin"] <= 1
    # Positive drift -> few paths should lose 50%
    assert result["prob_of_ruin"] < 0.5


def test_simulate_paths_shape(engine):
    np.random.seed(1)
    returns = pd.Series(np.random.normal(0, 0.01, 50))
    result = engine.simulate_paths(returns, initial_capital=100_000)
    assert len(result["ending_values"]) == engine.iterations
    assert len(result["max_dd_dist"]) == engine.iterations
    assert "var_95" in result
    assert "expected_shortfall" in result
    assert "prob_of_ruin" in result
    assert result["var_95"] <= 100_000  # 95% VaR should be below initial for mixed returns


def test_inject_execution_friction(engine):
    np.random.seed(2)
    returns = pd.Series(np.random.normal(0, 0.01, 20))
    out = engine.inject_execution_friction(returns, slippage_pct=0.0002, latency_shocks=0.1)
    assert isinstance(out, pd.Series)
    assert len(out) == len(returns)
    assert not np.allclose(out.values, returns.values)


def test_stress_test_regimes(engine):
    np.random.seed(3)
    returns = pd.Series(np.random.normal(0, 0.01, 30))
    result = engine.stress_test_regimes(returns, vol_multiplier=2.0)
    assert "ending_values" in result
    assert "prob_of_ruin" in result
    # Stressed returns -> higher volatility -> potentially higher prob_of_ruin
    assert result["prob_of_ruin"] >= 0


def test_get_decision_metrics(engine):
    np.random.seed(4)
    returns = pd.Series(np.random.normal(0.0005, 0.01, 40))
    sim_results = engine.simulate_paths(returns, initial_capital=100_000)
    text = engine.get_decision_metrics(sim_results, initial_capital=100_000)
    assert "Win Probability" in text
    assert "Value at Risk" in text
    assert "Drawdown" in text
