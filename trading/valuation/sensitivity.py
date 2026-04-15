"""
Monte Carlo Sensitivity Analysis
==================================
Wraps any valuation engine and runs N simulations with varied parameters
to produce a percentile-based fair value distribution.
"""

import numpy as np
from typing import Optional

from trading.valuation.sector_data import get_sector_profile


class SensitivityAnalysis:
    """
    Monte Carlo wrapper for any valuation engine.

    Varies discount rate, growth rate, and terminal growth within ranges,
    runs N simulations, and returns percentile statistics.
    """

    def __init__(self, engine, n_simulations: int = 1000, seed: Optional[int] = None):
        self.engine = engine
        self.n_simulations = n_simulations
        self.rng = np.random.default_rng(seed)

    def _detect_engine_type(self) -> str:
        """Detect engine type for parameter mapping."""
        cls_name = type(self.engine).__name__
        if "Growth" in cls_name:
            return "growth"
        elif "Revenue" in cls_name:
            return "revenue"
        return "classic"

    def _build_kwargs(
        self,
        ticker_symbol: str,
        discount_rate: float,
        growth_rate: float,
        perpetual_growth: float,
    ) -> dict:
        """Map generic parameters to engine-specific keyword arguments."""
        engine_type = self._detect_engine_type()

        if engine_type == "growth":
            return {
                "ticker_symbol": ticker_symbol,
                "discount_rate_override": discount_rate,
                "growth_override": growth_rate,
                "perpetual_growth": perpetual_growth,
            }
        elif engine_type == "revenue":
            # Revenue engine uses base_multiple_override instead of discount rate.
            # We derive a synthetic multiple from growth: higher growth → higher multiple.
            base_multiple = max(1.0, growth_rate * 30.0 + 3.0)
            return {
                "ticker_symbol": ticker_symbol,
                "base_multiple_override": base_multiple,
            }
        else:  # classic
            return {
                "ticker_symbol": ticker_symbol,
                "required_return": discount_rate,
                "growth_stage2_rate": growth_rate,
                "perpetual_growth": perpetual_growth,
            }

    def _get_parameter_ranges(
        self, sector: Optional[str] = None
    ) -> dict:
        """
        Return triangular distribution parameters (low, mode, high) for each input.

        If a sector is provided, ranges are narrowed/widened based on
        sector characteristics.
        """
        profile = get_sector_profile(sector) if sector else None

        # Base ranges
        dr_low, dr_mode, dr_high = 0.06, 0.09, 0.14
        gr_low, gr_mode, gr_high = -0.05, 0.08, 0.40
        pg_low, pg_mode, pg_high = 0.015, 0.025, 0.035

        if profile:
            expected = profile["expected_growth"]
            adj = profile["discount_rate_adj"]

            # Centre growth range on sector expectation
            gr_mode = expected
            gr_low = max(-0.10, expected - 0.15)
            gr_high = min(0.60, expected + 0.20)

            # Shift discount rate range by sector adjustment
            dr_mode += adj
            dr_low += adj
            dr_high += adj

        return {
            "discount_rate": (dr_low, dr_mode, dr_high),
            "growth_rate": (gr_low, gr_mode, gr_high),
            "perpetual_growth": (pg_low, pg_mode, pg_high),
        }

    def run(
        self,
        ticker_symbol: str,
        sector: Optional[str] = None,
        discount_rate_range: Optional[tuple] = None,
        growth_rate_range: Optional[tuple] = None,
        perpetual_growth_range: Optional[tuple] = None,
    ) -> dict:
        """
        Run N simulations and return distribution statistics.

        Parameters
        ----------
        ticker_symbol          : Stock ticker.
        sector                 : GICS sector name (for informed ranges).
        discount_rate_range    : Override (low, mode, high) for discount rate.
        growth_rate_range      : Override (low, mode, high) for growth rate.
        perpetual_growth_range : Override (low, mode, high) for terminal growth.

        Returns
        -------
        dict with percentiles (p10–p90), mean, std_dev, and parameter_ranges.
        """
        # Warm the cache with a single API call
        self.engine.calculate_dcf_fair_value(ticker_symbol)

        ranges = self._get_parameter_ranges(sector)
        if discount_rate_range:
            ranges["discount_rate"] = discount_rate_range
        if growth_rate_range:
            ranges["growth_rate"] = growth_rate_range
        if perpetual_growth_range:
            ranges["perpetual_growth"] = perpetual_growth_range

        dr_params = ranges["discount_rate"]
        gr_params = ranges["growth_rate"]
        pg_params = ranges["perpetual_growth"]

        fair_values = []
        for _ in range(self.n_simulations):
            dr = self.rng.triangular(*dr_params)
            gr = self.rng.triangular(*gr_params)
            pg = self.rng.triangular(*pg_params)

            # Ensure perpetual_growth < discount_rate (Gordon model constraint)
            if pg >= dr:
                pg = dr - 0.01

            kwargs = self._build_kwargs(ticker_symbol, dr, gr, pg)
            try:
                fv = self.engine.calculate_dcf_fair_value(**kwargs)
                if fv > 0:
                    fair_values.append(fv)
            except Exception:
                continue

        if not fair_values:
            return {"ticker": ticker_symbol, "error": "All simulations failed"}

        arr = np.array(fair_values)

        return {
            "ticker": ticker_symbol,
            "n_simulations": len(fair_values),
            "p10": round(float(np.percentile(arr, 10)), 2),
            "p25": round(float(np.percentile(arr, 25)), 2),
            "p50_median": round(float(np.percentile(arr, 50)), 2),
            "p75": round(float(np.percentile(arr, 75)), 2),
            "p90": round(float(np.percentile(arr, 90)), 2),
            "mean": round(float(np.mean(arr)), 2),
            "std_dev": round(float(np.std(arr)), 2),
            "parameter_ranges": ranges,
        }

    @staticmethod
    def print_report(results: dict):
        """Pretty-print sensitivity analysis results."""
        if "error" in results:
            print(f"\n  Sensitivity ERROR: {results['error']}")
            return

        print(f"\n  {'=' * 50}")
        print(f"  MONTE CARLO SENSITIVITY ANALYSIS")
        print(f"  {'=' * 50}")
        print(f"  Ticker       : {results['ticker']}")
        print(f"  Simulations  : {results['n_simulations']}")
        print(f"  {'-' * 50}")
        print(f"  P10 (bear)   : {results['p10']:>10.2f}")
        print(f"  P25          : {results['p25']:>10.2f}")
        print(f"  P50 (median) : {results['p50_median']:>10.2f}")
        print(f"  P75          : {results['p75']:>10.2f}")
        print(f"  P90 (bull)   : {results['p90']:>10.2f}")
        print(f"  {'-' * 50}")
        print(f"  Mean         : {results['mean']:>10.2f}")
        print(f"  Std Dev      : {results['std_dev']:>10.2f}")
        print(f"  {'=' * 50}")

        ranges = results.get("parameter_ranges", {})
        if ranges:
            print(f"  Parameter Ranges (low / mode / high):")
            for param, (lo, md, hi) in ranges.items():
                print(f"    {param:20s}: {lo:.3f} / {md:.3f} / {hi:.3f}")
