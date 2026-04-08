"""Base class for trading strategies."""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Optional

import pandas as pd


class Signal(Enum):
    """Trading signal types."""

    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class Trade:
    """Represents an executed trade."""

    ticker: str
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    quantity: float = 0.0
    profit_loss: float = 0.0
    pct_return: float = 0.0
    reason: str = ""

    @property
    def is_open(self) -> bool:
        return self.exit_date is None


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, config: dict):
        self.config = config
        self.fair_value: Optional[float] = None

    @abstractmethod
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add indicators and prepare data for signal generation."""
        pass

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, current_idx: int) -> Signal:
        """Generate a BUY, SELL, or HOLD signal for the current index."""
        pass

    def update_valuation(self, ticker: str):
        """Update the fair value estimate for the current ticker."""
        from trading.valuation import get_valuation_engine
        
        # Get engine choice from config, default to 'classic'
        engine_type = self.config.get("strategy", {}).get("valuation_engine", "classic")
        engine = get_valuation_engine(engine_type)
        
        try:
            # We use calculate_dcf_fair_value which is common to both
            self.fair_value = engine.calculate_dcf_fair_value(ticker)
        except Exception as e:
            print(f"Valuation error: {e}")
            self.fair_value = None
