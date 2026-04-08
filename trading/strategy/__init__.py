"""Strategy registry and factory."""

from trading.strategy.base import BaseStrategy, Signal, Trade
from trading.strategy.sma_rsi_macd import SmaRsiMacdStrategy
from trading.strategy.valuation_overlay import ValuationOverlayStrategy

STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "sma_rsi_macd": SmaRsiMacdStrategy,
    "valuation_overlay": ValuationOverlayStrategy,
}


def get_strategy(name: str, config: dict) -> BaseStrategy:
    """Get a strategy instance by name."""
    if name not in STRATEGY_REGISTRY:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    return STRATEGY_REGISTRY[name](config)


__all__ = ["BaseStrategy", "Signal", "Trade", "get_strategy", "STRATEGY_REGISTRY"]
