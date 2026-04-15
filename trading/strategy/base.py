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
        self.valuation_metrics: dict = {}

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
        strat_cfg = self.config.get("strategy", {})
        engine_type = strat_cfg.get("valuation_engine", "classic")
        engine = get_valuation_engine(engine_type)
        
        # Build arguments for the engine from config
        kwargs = {"ticker_symbol": ticker}
        
        # Mapping config keys to engine-specific kwargs
        if "perpetual_growth" in strat_cfg:
            kwargs["perpetual_growth"] = strat_cfg["perpetual_growth"]
            
        if "required_return" in strat_cfg:
            if engine_type == "growth":
                kwargs["discount_rate_override"] = strat_cfg["required_return"]
            else:
                kwargs["required_return"] = strat_cfg["required_return"]
                
        # Handle engine-specific stages/horizons if present in config
        if engine_type == "classic":
            if "projection_years" in strat_cfg:
                kwargs["projection_years"] = strat_cfg["projection_years"]
        elif engine_type == "growth":
            if "stage1_years" in strat_cfg:
                kwargs["stage1_years"] = strat_cfg["stage1_years"]
            if "stage2_years" in strat_cfg:
                kwargs["stage2_years"] = strat_cfg["stage2_years"]
        
        try:
            # Get full metrics dictionary
            metrics = engine.get_valuation_metrics(**kwargs)
            self.valuation_metrics = metrics
            self.fair_value = metrics.get("fair_value_bull")
        except Exception as e:
            print(f"Valuation error: {e}")
            self.fair_value = None
            self.valuation_metrics = {"error": str(e)}

