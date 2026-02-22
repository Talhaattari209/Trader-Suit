"""
Edge modules: Statistical, Pattern-Based, Volume, Market Structure,
Tokenized Assets, Geopolitical, Prediction/Event, AI-Enhanced.
See Different_Edges/IMPLEMENTATION_PLAN.md and edge_registry for mapping.
"""
from .edge_registry import get_edge_info, EDGE_REGISTRY, EdgeInfo
from .base_workflow import BaseEdgeWorkflow

__all__ = [
    "get_edge_info",
    "EDGE_REGISTRY",
    "EdgeInfo",
    "BaseEdgeWorkflow",
    "run_edge_by_type",
]


def run_edge_by_type(
    edge_type: str,
    csv_path: str | None = None,
) -> tuple[bool, dict]:
    """Run the workflow for the given edge_type. Returns (approved, metrics)."""
    info = get_edge_info(edge_type)
    if not info:
        return False, {"reason": f"Unknown edge_type: {edge_type}"}
    if edge_type == "statistical":
        from .statistical_workflow import run_statistical_workflow
        return run_statistical_workflow(csv_path=csv_path)
    if edge_type == "pattern_based":
        from .pattern_based.pattern_workflow import run_pattern_edge
        return run_pattern_edge(csv_path=csv_path)
    if edge_type == "volume_based":
        from .volume_based.volume_workflow import run_volume_edge
        return run_volume_edge(csv_path=csv_path)
    if edge_type == "market_structure":
        from .market_structure_workflow import run_market_structure_edge
        return run_market_structure_edge(csv_path=csv_path)
    if edge_type == "tokenized_assets":
        from .tokenized_workflow import run_tokenized_edge
        return run_tokenized_edge()
    if edge_type == "geopolitical":
        from .geo_workflow import run_geo_edge
        return run_geo_edge(csv_path=csv_path)
    if edge_type == "prediction_event":
        from .prediction_event.executor import run_prediction_event_edge
        return run_prediction_event_edge()
    if edge_type == "ai_enhanced":
        from .ai_enhanced_workflow import run_ai_enhanced_edge
        return run_ai_enhanced_edge(csv_path=csv_path)
    return False, {"reason": f"No workflow for edge_type: {edge_type}"}
