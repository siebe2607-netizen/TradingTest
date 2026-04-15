"""
Revenue Multiple Valuation Engine
===================================
Values stocks using growth-adjusted Price-to-Sales (P/S) multiples.
Designed for high-growth or pre-profit companies where FCF-based DCF
produces unreliable results (negative free cash flow).

Uses sector-aware base multiples from ``sector_data`` and adjusts them
for the company's growth rate relative to sector expectations.
"""

import time
from typing import Optional

import pandas as pd
import yfinance as yf

from trading.valuation.cache import FundamentalCache
from trading.valuation.sector_data import get_sector_profile


class RevenueMultipleEngine:
    """
    Fair value via growth-adjusted revenue multiples.

    Formula
    -------
    fair_value = (trailing_revenue × adjusted_PS_multiple) / shares_outstanding
    """

    def __init__(self, sleep_seconds: float = 1.5):
        self.sleep_seconds = sleep_seconds
        self.cache = FundamentalCache()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_growth(raw: float) -> float:
        """Normalise yfinance growth values (same logic as GrowthValuationEngine)."""
        if abs(raw) > 1.0:
            raw = raw / 100.0
        return max(-0.30, min(1.20, raw))

    def _fetch_fundamentals(self, ticker_symbol: str) -> dict:
        """Fetch revenue, shares, growth, and sector from yfinance."""
        cached = self.cache.get(ticker_symbol)
        if cached and "revenue" in cached:
            return cached

        time.sleep(self.sleep_seconds)
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info or len(info) < 10:
            raise ValueError("Rate limited or empty info from yfinance")

        revenue = info.get("totalRevenue")
        shares = info.get("sharesOutstanding")
        if not revenue or not shares or revenue <= 0:
            raise ValueError(
                f"Insufficient data: Revenue={revenue}, Shares={shares}"
            )

        # Weighted growth (same approach as growth engine)
        sources = {
            "earningsGrowth": 1.0,
            "earningsQuarterlyGrowth": 0.5,
            "revenueGrowth": 0.4,
        }
        weighted_sum = 0.0
        total_weight = 0.0
        for field, weight in sources.items():
            val = info.get(field)
            if val is not None:
                weighted_sum += self._normalise_growth(val) * weight
                total_weight += weight

        growth_rate = (weighted_sum / total_weight) if total_weight > 0 else 0.08
        growth_rate = max(-0.30, min(1.20, growth_rate))

        sector = info.get("sector", "")
        industry = info.get("industry", "")

        data = {
            "revenue": float(revenue),
            "shares_outstanding": float(shares),
            "growth_rate": growth_rate,
            "sector": sector,
            "industry": industry,
        }
        self.cache.set(ticker_symbol, data)
        return data

    @staticmethod
    def _adjusted_multiple(
        base: float, growth_rate: float, expected_growth: float
    ) -> float:
        """
        Scale the base P/S multiple for growth relative to sector expectations.

        Grows linearly: multiple × (1 + (growth − expected) / expected),
        clamped to [0.5×base, 2.0×base].
        """
        if expected_growth <= 0:
            expected_growth = 0.05
        ratio = (growth_rate - expected_growth) / expected_growth
        adjusted = base * (1.0 + ratio)
        return max(0.5 * base, min(2.0 * base, adjusted))

    # ------------------------------------------------------------------
    # Core valuation (interface-compatible method name)
    # ------------------------------------------------------------------

    def calculate_dcf_fair_value(
        self,
        ticker_symbol: str,
        base_multiple_override: Optional[float] = None,
        **kwargs,
    ) -> float:
        """
        Fair value = (trailing_revenue × adjusted_multiple) / shares.

        Despite the method name (kept for interface compatibility with the
        DCF engines), this is a revenue-multiple valuation, not a DCF.
        """
        fund = self._fetch_fundamentals(ticker_symbol)
        profile = get_sector_profile(fund["sector"])
        base = base_multiple_override or profile["base_ps_multiple"]
        adjusted = self._adjusted_multiple(
            base, fund["growth_rate"], profile["expected_growth"]
        )
        fair_value = (fund["revenue"] * adjusted) / fund["shares_outstanding"]
        return round(float(fair_value), 2)

    # ------------------------------------------------------------------
    # Public metrics
    # ------------------------------------------------------------------

    def get_valuation_metrics(
        self,
        ticker_symbol: str,
        conservative_growth: Optional[float] = None,
        base_multiple_override: Optional[float] = None,
        **kwargs,
    ) -> dict:
        """Full valuation snapshot matching the interface of ValuationEngine."""
        try:
            # --- Robust Price Fetch ---
            time.sleep(self.sleep_seconds)
            ticker = yf.Ticker(ticker_symbol)

            current_price = ticker.fast_info.get("lastPrice")
            if current_price is None or pd.isna(current_price):
                current_price = (
                    ticker.info.get("currentPrice")
                    or ticker.info.get("regularMarketPrice")
                )
            if current_price is None or pd.isna(current_price):
                hist = ticker.history(period="10d")["Close"].dropna()
                if not hist.empty:
                    current_price = float(hist.iloc[-1])
            if current_price is None or pd.isna(current_price):
                raise ValueError(f"No price data for {ticker_symbol}")
            current_price = float(current_price)

            # --- Bull case ---
            fair_value_bull = self.calculate_dcf_fair_value(
                ticker_symbol, base_multiple_override=base_multiple_override
            )

            fund = self._fetch_fundamentals(ticker_symbol)
            profile = get_sector_profile(fund["sector"])
            base = base_multiple_override or profile["base_ps_multiple"]
            ps_used = self._adjusted_multiple(
                base, fund["growth_rate"], profile["expected_growth"]
            )

            result = {
                "ticker": ticker_symbol,
                "current_price": round(current_price, 2),
                "fair_value_bull": fair_value_bull,
                "trailing_revenue": round(fund["revenue"], 0),
                "ps_multiple_used": round(ps_used, 2),
                "sector": fund["sector"],
                "growth_rate_pct": round(fund["growth_rate"] * 100, 1),
                "engine": "revenue",
            }

            # --- Bear case ---
            if conservative_growth is not None:
                bear_ps = self._adjusted_multiple(
                    base, conservative_growth, profile["expected_growth"]
                )
                fair_value_bear = (
                    fund["revenue"] * bear_ps
                ) / fund["shares_outstanding"]
                fair_value_bear = round(float(fair_value_bear), 2)
                result["fair_value_bear"] = fair_value_bear
                result["conservative_growth_pct"] = round(
                    conservative_growth * 100, 1
                )
                result["fair_value_mid"] = round(
                    (fair_value_bull + fair_value_bear) / 2, 2
                )

            best_estimate = result.get("fair_value_mid", fair_value_bull)
            upside = (best_estimate - current_price) / current_price
            result["upside_pct"] = round(upside * 100, 2)
            result["is_undervalued"] = upside > 0.20

            return result

        except Exception as e:
            return {"ticker": ticker_symbol, "error": str(e)}
