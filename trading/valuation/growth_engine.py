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

    # Forward estimate blending weights
    FORWARD_WEIGHT: float = 0.6
    HISTORICAL_WEIGHT: float = 0.4

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
            # Check if it looks like a whole percentage (e.g. 27.0) vs a massive multiplier (e.g. 200.0)
            # Most companies don't sustain > 500% growth. If it's > 5 and looks like an int, it's likely a pct.
            raw = raw / 100.0
        # Realistic bounds for Stage 1: -30% … +120%
        return max(-0.30, min(1.20, raw))

    def _fetch_forward_estimates(self, ticker) -> Optional[float]:
        """
        Attempt to extract analyst consensus forward growth estimates.

        Tries ``ticker.growth_estimates`` and ``ticker.earnings_estimate``
        from yfinance. Returns a normalised growth rate or None.
        """
        try:
            ge = ticker.growth_estimates
            if ge is not None and not ge.empty:
                # growth_estimates is a DataFrame with index like
                # ['0q', '+1q', '0y', '+1y', '+5y', '-5y'] and columns per ticker.
                # We want the "+1y" (next year) row.
                for label in ["+1y", "0y", "+1q"]:
                    if label in ge.index:
                        val = ge.loc[label].iloc[0]
                        if val is not None and not pd.isna(val):
                            return self._normalise_growth(float(val))
        except Exception:
            pass

        try:
            ee = ticker.earnings_estimate
            if ee is not None and not ee.empty:
                # earnings_estimate has columns like 'avg', 'low', 'high'
                # and index like '0y', '+1y'. Compute YoY growth from avg.
                if "avg" in ee.columns and len(ee) >= 2:
                    current = ee["avg"].iloc[0]
                    next_yr = ee["avg"].iloc[1]
                    if (
                        current is not None
                        and next_yr is not None
                        and not pd.isna(current)
                        and not pd.isna(next_yr)
                        and current != 0
                    ):
                        yoy = (next_yr - current) / abs(current)
                        return self._normalise_growth(float(yoy))
        except Exception:
            pass

        return None

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

        # Growth sources and their weights
        # Higher weights = more influence on the final blended growth rate
        sources = {
            "earningsGrowth": 1.0,           # Standard forward-looking earnings growth
            "earningsQuarterlyGrowth": 0.5,  # Recent performance (noisier)
            "revenueGrowth": 0.4             # Top-line growth (conservative fallback)
        }

        weighted_growth_sum = 0.0
        total_weight = 0.0

        for field, weight in sources.items():
            val = info.get(field)
            if val is not None:
                norm_val = self._normalise_growth(val)
                weighted_growth_sum += (norm_val * weight)
                total_weight += weight

        if total_weight > 0:
            historical_growth = weighted_growth_sum / total_weight
            historical_growth = max(-0.30, min(1.20, historical_growth))
        else:
            historical_growth = 0.10

        # Blend with analyst forward estimates when available
        forward_growth = self._fetch_forward_estimates(ticker)
        if forward_growth is not None:
            growth_rate = (
                forward_growth * self.FORWARD_WEIGHT
                + historical_growth * self.HISTORICAL_WEIGHT
            )
            growth_rate_source = "blended"
        else:
            growth_rate = historical_growth
            growth_rate_source = "historical_only"

        growth_rate = max(-0.30, min(1.20, growth_rate))

        beta = info.get("beta") or 1.0

        data = {
            "fcf": current_fcf,
            "shares_outstanding": shares_outstanding,
            "growth_rate": growth_rate,
            "beta": beta,
            "growth_rate_source": growth_rate_source,
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
        forward_weight: Optional[float] = None,
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
        forward_weight          : Override the forward/historical blend weight (0-1).
        """
        # Apply custom forward weight if specified (before fetching fundamentals)
        original_fw = self.FORWARD_WEIGHT
        original_hw = self.HISTORICAL_WEIGHT
        if forward_weight is not None:
            self.FORWARD_WEIGHT = forward_weight
            self.HISTORICAL_WEIGHT = 1.0 - forward_weight
            # Invalidate cache so new weight takes effect
            self.cache._cache.pop(ticker_symbol, None)
        try:
            fund = self._fetch_fundamentals(ticker_symbol)
        finally:
            # Restore original weights
            self.FORWARD_WEIGHT = original_fw
            self.HISTORICAL_WEIGHT = original_hw

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
                "growth_rate_source": fund.get("growth_rate_source", "historical_only"),
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
