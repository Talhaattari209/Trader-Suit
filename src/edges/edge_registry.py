"""
Edge registry: maps user intent / edge_type to modules, models, and data sources.
Used by Instruction Router and LLM (Librarian/Strategist) to select workflows.
See Different_Edges/IMPLEMENTATION_PLAN.md.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EdgeInfo:
    edge_type: str
    keywords: List[str]
    core_modules: List[str]
    models_used: List[str]
    data_sources: List[str]
    workflow_module: Optional[str] = None


EDGE_REGISTRY: List[EdgeInfo] = [
    EdgeInfo(
        edge_type="statistical",
        keywords=["pairs trading", "cointegration", "z-score", "mean reversion", "statistical arb"],
        core_modules=["src.edges.statistical_edges", "src.data.preprocessor"],
        models_used=["XGBoost", "KMeans", "LSTM", "PPO"],
        data_sources=["Polygon", "US30 loader"],
        workflow_module="src.edges.statistical_workflow",
    ),
    EdgeInfo(
        edge_type="pattern_based",
        keywords=["head-and-shoulders", "candlestick", "chart pattern", "pattern"],
        core_modules=["src.edges.pattern_based.pattern_workflow", "src.edges.pattern_based.pattern_detector_ml"],
        models_used=["RandomForest", "Boruta", "CNN", "LSTM", "PPO"],
        data_sources=["US30", "Polygon OHLCV"],
        workflow_module="src.edges.pattern_based.pattern_workflow",
    ),
    EdgeInfo(
        edge_type="volume_based",
        keywords=["volume spike", "VWAP", "TWAP", "institutional", "volume"],
        core_modules=["src.edges.volume_based.volume_analyzer", "src.edges.volume_based.volume_rl_agent"],
        models_used=["RandomForest", "CNN", "PPO"],
        data_sources=["Polygon tick/agg"],
        workflow_module="src.edges.volume_based.volume_workflow",
    ),
    EdgeInfo(
        edge_type="market_structure",
        keywords=["ICT", "order block", "FVG", "BOS", "liquidity sweep", "market structure"],
        core_modules=["src.edges.market_structure", "src.agents.structure_agent", "src.ml.regime_classifier"],
        models_used=["Hurst", "RandomForest", "Transformer", "DQN"],
        data_sources=["Alpaca", "US30"],
        workflow_module="src.edges.market_structure_workflow",
    ),
    EdgeInfo(
        edge_type="tokenized_assets",
        keywords=["tokenized RWA", "cross-chain arb", "BUIDL", "gas", "tokenized asset"],
        core_modules=["src.edges.tokenized_assets", "src.connectors.coingecko_connector"],
        models_used=["XGBoost", "GNN", "DQN"],
        data_sources=["CoinGecko"],
        workflow_module="src.edges.tokenized_workflow",
    ),
    EdgeInfo(
        edge_type="geopolitical",
        keywords=["EM", "multipolar", "USD weak", "regime", "conflict", "geopolitical"],
        core_modules=["src.agents.geo_agent", "src.ml.regime_clustering", "src.rl.ppo_geo"],
        models_used=["GARCH", "LSTM", "KMeans", "PPO"],
        data_sources=["Polygon EEM", "X/news"],
        workflow_module="src.edges.geo_workflow",
    ),
    EdgeInfo(
        edge_type="prediction_event",
        keywords=["prediction market", "Polymarket", "Kalshi", "earnings", "calendar", "event"],
        core_modules=["src.edges.prediction_event.data_fetchers", "src.edges.prediction_event.models_ml"],
        models_used=["XGBoost", "Transformer", "PPO"],
        data_sources=["Polymarket", "Kalshi", "Trading Economics"],
        workflow_module="src.edges.prediction_event.executor",
    ),
    EdgeInfo(
        edge_type="ai_enhanced",
        keywords=["sentiment", "factor mining", "momentum", "arbitrage", "microstructure", "hybrid"],
        core_modules=["src.edges.sentiment_news", "src.edges.factor_mining", "src.edges.momentum_reversion"],
        models_used=["BERT", "XGBoost", "Autoencoder", "LSTM", "PPO"],
        data_sources=["RSS", "X", "us30_loader"],
        workflow_module="src.edges.ai_enhanced_workflow",
    ),
]


def get_edge_info(edge_type: str) -> Optional[EdgeInfo]:
    """Return EdgeInfo for a given edge_type (e.g. 'statistical', 'pattern_based')."""
    for info in EDGE_REGISTRY:
        if info.edge_type == edge_type:
            return info
    return None


def match_instruction_to_edges(instruction: str) -> List[EdgeInfo]:
    """
    Simple keyword match: return edge(s) whose keywords appear in instruction.
    For production, use LLM to classify intent and return one or more edge types.
    """
    instruction_lower = instruction.lower()
    matched = []
    for info in EDGE_REGISTRY:
        if any(kw in instruction_lower for kw in info.keywords):
            matched.append(info)
    return matched if matched else EDGE_REGISTRY  # fallback: all edges (or leave empty)


def registry_summary_for_llm() -> str:
    """Short summary of edge types and modules for inclusion in Strategist/Librarian prompts."""
    lines = [
        "Edge registry (use these when generating code):",
        *[
            f"- {e.edge_type}: modules {e.core_modules[0]}; workflow {e.workflow_module or 'N/A'}"
            for e in EDGE_REGISTRY
        ],
    ]
    return "\n".join(lines)
