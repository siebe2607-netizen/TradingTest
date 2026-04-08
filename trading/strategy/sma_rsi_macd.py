"""Strategy combining SMA crossover, RSI, MACD, and Bollinger Bands."""

import pandas as pd
from trading.strategy.base import BaseStrategy, Signal
from trading.indicators import technical


class SmaRsiMacdStrategy(BaseStrategy):
    """Strategy using SMA, RSI, MACD, and Bollinger Bands."""

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all required technical indicators."""
        return technical.add_all_indicators(df, self.config)

    def generate_signal(self, df: pd.DataFrame, current_idx: int) -> Signal:
        """Generate trading signal based on multi-indicator logic."""
        if current_idx < 1:
            return Signal.HOLD

        row = df.iloc[current_idx]
        prev_row = df.iloc[current_idx - 1]

        cfg = self.config["strategy"]
        sma_s = f"SMA_{cfg['sma_short_period']}"
        sma_l = f"SMA_{cfg['sma_long_period']}"

        # 1. SMA Crossover (Golden Cross / Death Cross)
        uptrend = row[sma_s] > row[sma_l]
        crossover_up = prev_row[sma_s] <= prev_row[sma_l] and uptrend
        crossover_down = prev_row[sma_s] >= prev_row[sma_l] and not uptrend

        # 2. RSI
        rsi_oversold = row["RSI"] < cfg["rsi_oversold"]
        rsi_overbought = row["RSI"] > cfg["rsi_overbought"]

        # 3. MACD
        macd_positive = row["MACD_Hist"] > 0
        macd_flip_down = prev_row["MACD_Hist"] > 0 and row["MACD_Hist"] <= 0

        # BUY Signal Logic
        # - SMA Golden Cross OR (Uptrend AND MACD positive)
        # - Not overbought
        # - Price near or below lower Bollinger Band
        if (crossover_up or (uptrend and macd_positive)) and not rsi_overbought:
            if row["Close"] < row["BB_Lower"] * 1.05:  # Pullback/Value entry
                return Signal.BUY

        # SELL Signal Logic
        # - SMA Death Cross
        # - OR RSI Overbought
        # - OR MACD histogram flips negative
        if crossover_down or rsi_overbought or macd_flip_down:
            return Signal.SELL

        return Signal.HOLD
