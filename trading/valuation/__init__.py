"""
Factory for valuation engines.

Usage
-----
    from trading.valuation import get_valuation_engine

    engine = get_valuation_engine("classic")   # original 5-year flat DCF
    engine = get_valuation_engine("growth")    # 10-year CAPM + decay DCF
"""

from typing import Union

from trading.valuation.engine import ValuationEngine
from trading.valuation.growth_engine import GrowthValuationEngine

ENGINES = {
    "classic": ValuationEngine,
    "growth":  GrowthValuationEngine,
}


def get_valuation_engine(
    name: str = "classic",
    sleep_seconds: float = 1.5,
) -> Union[ValuationEngine, GrowthValuationEngine]:
    """
    Return an engine instance by name.

    Parameters
    ----------
    name          : "classic" (5-year flat) | "growth" (10-year CAPM decay)
    sleep_seconds : Seconds to sleep between Yahoo Finance calls.
    """
    name = name.lower().strip()
    if name not in ENGINES:
        raise ValueError(
            f"Unknown engine '{name}'. Available: {list(ENGINES.keys())}"
        )
    return ENGINES[name](sleep_seconds=sleep_seconds)
