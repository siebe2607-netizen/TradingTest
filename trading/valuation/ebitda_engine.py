"""
EV/EBITDA Valuation Engine
===================================
Values stocks using growth-adjusted Enterprise Value-to-EBITDA multiples.
Perfect for cash-heavy, highly profitable companies like Adyen.

Uses sector-aware base multiples from ``sector_data`` and adjusts them
for the company's growth rate relative to sector expectations.
Enterprise Value (EV) = Market Cap + Debt - Cash.
"""

import time
from typing import Optional

import pandas as pd
import yfinance as yf

from trading.valuation.cache import FundamentalCache
from trading.valuation.sector_data import get_sector_profile


class EbitdaValuationEngine:
    """
    Fair value via growth-adjusted EV/EBITDA multiples.

    Formula
    -------
    expected_ev = ebitda * adjusted_ev_ebitda_multiple
    equity_value = expected_ev + total_cash - total_debt
    fair_value = equity_value / shares_outstanding
    """

    def __init__(self, sleep_seconds: float = 1.5):
        self.sleep_seconds = sleep_seconds
        self.cache = FundamentalCache()

    @staticmethod
    def _normalise_growth(raw: float) -> float:
        if abs(raw) > 1.0:
            raw = raw / 100.0
        return max(-0.30, min(1.20, raw))

    def _fetch_fundamentals(self, ticker_symbol: str) -> dict:
        cached = self.cache.get(ticker_symbol)
        if cached and "ebitda" in cached:
            return cached

        time.sleep(self.sleep_seconds)
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info or len(info) < 10:
            raise ValueError("Rate limited or empty info from yfinance")

        ebitda = info.get("ebitda")
        shares = info.get("sharesOutstanding")
        total_cash = info.get("totalCash", 0)
        total_debt = info.get("totalDebt", 0)

        if not ebitda or not shares or ebitda <= 0:
            raise ValueError(
                f"Insufficient data: EBITDA={ebitda}, Shares={shares}"
            )

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
            "ebitda": float(ebitda),
            "shares_outstanding": float(shares),
            "total_cash": float(total_cash),
            "total_debt": float(total_debt),
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
        if expected_growth <= 0:
            expected_growth = 0.05
        ratio = (growth_rate - expected_growth) / expected_growth
        adjusted = base * (1.0 + ratio)
        return max(0.5 * base, min(3.0 * base, adjusted))  # Wider range than revenue

    def calculate_dcf_fair_value(
        self,
        ticker_symbol: str,
        base_multiple_override: Optional[float] = None,
        **kwargs,
    ) -> float:
        fund = self._fetch_fundamentals(ticker_symbol)
        profile = get_sector_profile(fund["sector"])
        base = base_multiple_override or profile.get("base_ev_ebitda", 10.0)
        adjusted = self._adjusted_multiple(
            base, fund["growth_rate"], profile["expected_growth"]
        )
        expected_ev = fund["ebitda"] * adjusted
        equity_value = expected_ev + fund["total_cash"] - fund["total_debt"]
        fair_value = equity_value / fund["shares_outstanding"]
        return round(float(fair_value), 2)

    def get_valuation_metrics(
        self,
        ticker_symbol: str,
        conservative_growth: Optional[float] = None,
        base_multiple_override: Optional[float] = None,
        **kwargs,
    ) -> dict:
        try:
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

            fair_value_bull = self.calculate_dcf_fair_value(
                ticker_symbol, base_multiple_override=base_multiple_override
            )

            fund = self._fetch_fundamentals(ticker_symbol)
            profile = get_sector_profile(fund["sector"])
            base = base_multiple_override or profile.get("base_ev_ebitda", 10.0)
            multiple_used = self._adjusted_multiple(
                base, fund["growth_rate"], profile["expected_growth"]
            )

            result = {
                "ticker": ticker_symbol,
                "current_price": round(current_price, 2),
                "fair_value_bull": fair_value_bull,
                "trailing_ebitda": round(fund["ebitda"], 0),
                "total_cash": round(fund["total_cash"], 0),
                "total_debt": round(fund["total_debt"], 0),
                "ev_ebitda_multiple_used": round(multiple_used, 2),
                "sector": fund["sector"],
                "growth_rate_pct": round(fund["growth_rate"] * 100, 1),
                "engine": "ebitda",
            }

            if conservative_growth is not None:
                bear_mult = self._adjusted_multiple(
                    base, conservative_growth, profile["expected_growth"]
                )
                ev_bear = fund["ebitda"] * bear_mult
                equity_bear = ev_bear + fund["total_cash"] - fund["total_debt"]
                fair_value_bear = equity_bear / fund["shares_outstanding"]
                
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
