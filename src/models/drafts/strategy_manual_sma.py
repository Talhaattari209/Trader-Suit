from src.models.base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class MovingAverageCrossover(BaseStrategy):
    """
    Simple MACD-like strategy to test the pipeline.
    """
    def __init__(self):
        self.short_window = 20
        self.long_window = 50
        self.closes = []
        
    def entry(self, state: dict) -> bool:
        # We need history to calculate MA. 
        # Since the backtest loop in KillerAgent passes state bar by bar, 
        # we need to accumulate state or assume state has history.
        # But BaseStrategy state is just the current bar dict.
        # So we accumulate here.
        price = state["Close"]
        self.closes.append(price)
        
        if len(self.closes) < self.long_window:
            return False
            
        short_ma = np.mean(self.closes[-self.short_window:])
        long_ma = np.mean(self.closes[-self.long_window:])
        
        # Simple Golden Cross
        return short_ma > long_ma

    def exit(self, state: dict) -> bool:
        if len(self.closes) < self.long_window:
            return False
            
        short_ma = np.mean(self.closes[-self.short_window:])
        long_ma = np.mean(self.closes[-self.long_window:])
        
        return short_ma < long_ma

    def risk(self, state: dict) -> float:
        return 0.1  # Fixed position size
