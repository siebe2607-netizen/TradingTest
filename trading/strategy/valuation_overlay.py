"""Strategy overlay that combines technical signals with fundamental valuation."""

import pandas as pd
from trading.strategy.base import BaseStrategy, Signal
from trading.strategy.sma_rsi_macd import SmaRsiMacdStrategy


class ValuationOverlayStrategy(BaseStrategy):
    """
    Only buys if the underlying technical strategy signals BUY 
    AND the stock is fundamentally undervalued (Price < Fair Value).
    """

    def __init__(self, config: dict):
        super().__init__(config)
        # Use the default strategy as the technical base
        self.technical_strategy = SmaRsiMacdStrategy(config)
        self.margin_of_safety = config.get("risk", {}).get("margin_of_safety", 0.2)

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators."""
        return self.technical_strategy.prepare_data(df)

    def generate_signal(self, df: pd.DataFrame, current_idx: int) -> Signal:
        """Generate signal based on technicals + valuation check."""
        tech_signal = self.technical_strategy.generate_signal(df, current_idx)
        
        if tech_signal == Signal.BUY:
            if self.fair_value is None:
                # If no valuation, default to technicals (or could be conservative)
                return Signal.BUY
            
            current_price = df["Close"].iloc[current_idx]
            # Buy only if price is below Fair Value with a margin of safety
            if current_price < self.fair_value * (1 - self.margin_of_safety):
                print(f"VALUATION: BUY approved (Price {current_price:.2f} < Fair Value {self.fair_value:.2f})")
                return Signal.BUY
            else:
                print(f"VALUATION: BUY rejected (Price {current_price:.2f} > Fair Value target {(self.fair_value * (1 - self.margin_of_safety)):.2f})")
                return Signal.HOLD
                
        # For SELL, we can be more aggressive if overvalued, 
        # but here we just follow the technical SELL signal.
        return tech_signal
