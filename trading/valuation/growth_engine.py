"""
Growth-Sensitive Valuation Engine
==================================
A 10-year, 2-stage DCF model that:
  - Uses CAPM to derive a stock-specific discount rate (beta * ERP + rf)
  - Projects explicit cash flows for 10 years with growth decaying in Stage 2
  - Weights earnings growth heavier than revenue growth
  - Applies the same yfinance percentage-normalization fix (÷100 if >1)
"""

import time
from typing import Optional

import pandas as pd
import yfinance as yf

from trading.valuation.cache import FundamentalCache


class GrowthValuationEngine:
    """
    10-year DCF with CAPM discount rate and stage-wise growth decay.

    Stages
    ------
    Stage 1 (years 1-5)  : Full fetched growth rate (earnings > revenue).
    Stage 2 (years 6-10) : Growth linearly decays → perpetual_growth.
    Terminal             : Gordon Growth Model.
    """

    # CAPM parameters
    RISK_FREE_RATE: float = 0.042   # ~10Y German Bund / Treasury
    EQUITY_RISK_PREMIUM: float = 0.050  # Historical ERP for developed markets

    def __init__(self, sleep_seconds: float = 1.5):
        self.sleep_seconds = sleep_seconds
        self.cache = FundamentalCache()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_growth(raw: float) -> float:
        """Divide by 100 when yfinance returns whole-number percentages (e.g. 27.6 → 0.276)."""
        if abs(raw) > 1.0:
            raw = raw / 100.0
        # Realistic bounds: -30% … +60%
        return max(-0.30, min(0.60, raw))

    def _fetch_fundamentals(self, ticker_symbol: str) -> dict:
        """Fetch and cache fundamental data with rate-limit protection."""
        cached = self.cache.get(ticker_symbol)
        if cached and "beta" in cached:   # growth engine needs beta in cache too
            return cached

        time.sleep(self.sleep_seconds)
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info or len(info) < 10:
            raise ValueError("Rate limited or empty info from yfinance")

        cash_flow = ticker.cashflow
        if cash_flow.empty:
            raise ValueError("Empty cashflow data")

        # FCF detection
        fcf_labels = ["Free Cash Flow", "FreeCashFlow", "Operating Cash Flow", "OperatingCashFlow"]
        current_fcf = None
        for label in fcf_labels:
            if label in cash_flow.index:
                val = cash_flow.loc[label].iloc[0]
                if not pd.isna(val):
                    current_fcf = float(val)
                    break

        shares_outstanding = info.get("sharesOutstanding")
        if not shares_outstanding or current_fcf is None or current_fcf <= 0:
            raise ValueError(f"Insufficient data: FCF={current_fcf}, Shares={shares_outstanding}")

        # Growth: prefer earningsGrowth (more forward-looking), fallback to revenue
        earnings_growth = info.get("earningsGrowth")
        revenue_growth  = info.get("revenueGrowth")
        quarterly_growth = info.get("earningsQuarterlyGrowth")

        # Pick the highest credible growth signal (earnings weighted heavier)
        candidates = []
        if earnings_growth is not None:
            candidates.append(self._normalise_growth(earnings_growth) * 1.0)   # full weight
        if quarterly_growth is not None:
            candidates.append(self._normalise_growth(quarterly_growth) * 0.5)  # half weight (noisy)
        if revenue_growth is not None:
            candidates.append(self._normalise_growth(revenue_growth) * 0.3)    # lower weight

        # Weighted average of whatever signals were found
        if candidates:
            growth_rate = sum(candidates) / len(candidates)
            # Re-cap after blending
            growth_rate = max(-0.30, min(0.60, growth_rate))
        else:
            growth_rate = 0.10

        beta = info.get("beta") or 1.0

        data = {
            "fcf": current_fcf,
            "shares_outstanding": shares_outstanding,
            "growth_rate": growth_rate,
            "beta": beta,
        }
        self.cache.set(ticker_symbol, data)
        return data

    # ------------------------------------------------------------------
    # Core valuation
    # ------------------------------------------------------------------

    def calculate_dcf_fair_value(
        self,
        ticker_symbol: str,
        perpetual_growth: float = 0.025,
        stage1_years: int = 5,
        stage2_years: int = 5,
        growth_override: Optional[float] = None,
        discount_rate_override: Optional[float] = None,
    ) -> float:
        """
        2-stage DCF using CAPM discount rate and linear growth decay.

        Parameters
        ----------
        perpetual_growth        : Terminal (Gordon) growth rate.
        stage1_years            : High-growth phase length (default 5).
        stage2_years            : Fading-growth phase length (default 5).
        growth_override         : Pin the growth rate manually (bear/bull scenarios).
        discount_rate_override  : Pin the discount rate (bypasses CAPM).
        """
        fund = self._fetch_fundamentals(ticker_symbol)
        current_fcf     = fund["fcf"]
        shares          = fund["shares_outstanding"]
        growth_rate     = growth_override if growth_override is not None else fund["growth_rate"]
        beta            = fund["beta"]

        # CAPM discount rate
        if discount_rate_override is not None:
            required_return = discount_rate_override
        else:
            required_return = self.RISK_FREE_RATE + beta * self.EQUITY_RISK_PREMIUM

        total_years = stage1_years + stage2_years

        # Project FCFs
        pv_fcfs = []
        fcf = current_fcf

        for year in range(1, total_years + 1):
            if year <= stage1_years:
                g = growth_rate
            else:
                # Linear decay from growth_rate → perpetual_growth
                decay_step = year - stage1_years          # 1 … stage2_years
                fraction   = decay_step / stage2_years    # 0 → 1
                g = growth_rate + fraction * (perpetual_growth - growth_rate)

            fcf = fcf * (1 + g)
            pv  = fcf / ((1 + required_return) ** year)
            pv_fcfs.append(pv)

        # Terminal value
        terminal_fcf   = pv_fcfs[-1] * ((1 + required_return) ** total_years)  # un-discount last
        terminal_value = (terminal_fcf * (1 + perpetual_growth)) / (required_return - perpetual_growth)
        pv_terminal    = terminal_value / ((1 + required_return) ** total_years)

        enterprise_value = sum(pv_fcfs) + pv_terminal
        fair_value       = enterprise_value / shares
        return round(float(fair_value), 2)

    # ------------------------------------------------------------------
    # Public metrics (matches interface of ValuationEngine)
    # ------------------------------------------------------------------

    def get_valuation_metrics(
        self,
        ticker_symbol: str,
        perpetual_growth: float = 0.025,
        stage1_years: int = 5,
        stage2_years: int = 5,
        conservative_growth: Optional[float] = None,
        discount_rate_override: Optional[float] = None,
    ) -> dict:
        """Returns valuation snapshot. conservative_growth triggers a bear case."""
        try:
            # --- Robust Price Fetch ---
            time.sleep(self.sleep_seconds)
            ticker = yf.Ticker(ticker_symbol)
            
            # 1. Try fast_info
            current_price = ticker.fast_info.get('lastPrice')
            
            # 2. Try info currentPrice
            if current_price is None or pd.isna(current_price):
                current_price = ticker.info.get('currentPrice') or ticker.info.get('regularMarketPrice')
                
            # 3. Try history with NaN filtering
            if current_price is None or pd.isna(current_price):
                hist = ticker.history(period="10d")["Close"].dropna()
                if not hist.empty:
                    current_price = float(hist.iloc[-1])
            
            if current_price is None or pd.isna(current_price):
                raise ValueError(f"No price data for {ticker_symbol}")

            current_price = float(current_price)

            # --- Bull case ---
            fair_value_bull = self.calculate_dcf_fair_value(
                ticker_symbol,
                perpetual_growth=perpetual_growth,
                stage1_years=stage1_years,
                stage2_years=stage2_years,
                discount_rate_override=discount_rate_override,
            )

            # Fetch to get beta / growth for display
            fund = self._fetch_fundamentals(ticker_symbol)

            result = {
                "ticker":          ticker_symbol,
                "current_price":   round(current_price, 2),
                "fair_value_bull": fair_value_bull,
                "growth_rate_pct": round(fund["growth_rate"] * 100, 1),
                "beta":            round(fund["beta"], 2),
                "capm_rate_pct":   round(
                    (self.RISK_FREE_RATE + fund["beta"] * self.EQUITY_RISK_PREMIUM) * 100, 2
                ),
                "perpetual_growth_pct": round(perpetual_growth * 100, 1),
                "horizon_years": stage1_years + stage2_years,
                "engine": "growth",
            }

            if conservative_growth is not None:
                fair_value_bear = self.calculate_dcf_fair_value(
                    ticker_symbol,
                    perpetual_growth=perpetual_growth,
                    stage1_years=stage1_years,
                    stage2_years=stage2_years,
                    growth_override=conservative_growth,
                    discount_rate_override=discount_rate_override,
                )
                result["fair_value_bear"] = fair_value_bear
                result["conservative_growth_pct"] = round(conservative_growth * 100, 1)
                result["fair_value_mid"] = round(
                    (fair_value_bull + fair_value_bear) / 2, 2
                )

            best_estimate = result.get("fair_value_mid", fair_value_bull)
            upside = (best_estimate - current_price) / current_price
            result["upside_pct"]   = round(upside * 100, 2)
            result["is_undervalued"] = upside > 0.20

            return result

        except Exception as e:
            return {"ticker": ticker_symbol, "error": str(e)}
