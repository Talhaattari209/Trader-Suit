"""Volume analyst LLM (optional)."""
def volume_analyst_scan(df_reduced, context: str = "") -> str:
    return f"Volume analysis: spike_ratio in data. Hypothesis: enter on spike >150% avg. {context}"
