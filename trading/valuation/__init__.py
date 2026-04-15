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
from trading.valuation.revenue_engine import RevenueMultipleEngine
from trading.valuation.ebitda_engine import EbitdaValuationEngine

ENGINES = {
    "classic": ValuationEngine,
    "growth":  GrowthValuationEngine,
    "revenue": RevenueMultipleEngine,
    "ebitda":  EbitdaValuationEngine,
}


def get_valuation_engine(
    name: str = "classic",
    sleep_seconds: float = 1.5,
) -> Union[ValuationEngine, GrowthValuationEngine, RevenueMultipleEngine]:
    """
    Return an engine instance by name.

    Parameters
    ----------
    name          : "classic" (5-year flat) | "growth" (10-year CAPM decay) | "revenue" (P/S multiple) | "ebitda" (EV/EBITDA multiple)
    sleep_seconds : Seconds to sleep between Yahoo Finance calls.
    """
    name = name.lower().strip()
    if name not in ENGINES:
        raise ValueError(
            f"Unknown engine '{name}'. Available: {list(ENGINES.keys())}"
        )
    return ENGINES[name](sleep_seconds=sleep_seconds)
