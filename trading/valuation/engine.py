"""Valuation engine: DCF fair value + current price fetch with rate-limit protection."""

import time
from typing import Optional
import pandas as pd
import yfinance as yf

from trading.valuation.cache import FundamentalCache


class ValuationEngine:
    """Calculates fair value estimates using fundamental analysis."""

    def __init__(self, risk_free_rate: float = 0.04, sleep_seconds: float = 1.5):
        self.risk_free_rate = risk_free_rate
        self.sleep_seconds = sleep_seconds
        self.cache = FundamentalCache()

    def calculate_dcf_fair_value(
        self,
        ticker_symbol: str,
        projection_years: int = 5,
        perpetual_growth: float = 0.025,
        required_return: float = 0.09,
        growth_stage2_rate: Optional[float] = None,  # optional override for conservative 2nd stage
        em_adjustment: float = 0.0,
    ) -> float:
        """
        Intrinsic value per share using a 2-stage DCF model.

        Parameters
        ----------
        projection_years   : Number of years to project explicit cash flows (default 5).
        perpetual_growth   : Terminal/Gordon-growth rate after projection period (default 2.5%).
        required_return    : Discount rate / WACC (default 9%).
        growth_stage2_rate : If set, overrides the fetched earnings-growth rate used in stage 1.
                             Useful to tighten the upper bound of the valuation range.
        """

        # 1. Check Cache
        cached_data = self.cache.get(ticker_symbol)
        if cached_data:
            current_fcf = cached_data["fcf"]
            shares_outstanding = cached_data["shares_outstanding"]
            growth_rate = cached_data["growth_rate"]
        else:
            # Sleep before fetching to avoid Yahoo Finance rate limits
            time.sleep(self.sleep_seconds)

            ticker = yf.Ticker(ticker_symbol)
            try:
                info = ticker.info
                if not info or len(info) < 10:
                    raise ValueError("Rate limited or empty info from yfinance")

                cash_flow = ticker.cashflow
                if cash_flow.empty:
                    raise ValueError("Empty cashflow data")

                # Robust FCF detection across different yfinance label versions
                fcf_labels = [
                    "Free Cash Flow",
                    "FreeCashFlow",
                    "Operating Cash Flow",
                    "OperatingCashFlow",
                ]
                current_fcf = None
                for label in fcf_labels:
                    if label in cash_flow.index:
                        val = cash_flow.loc[label].iloc[0]
                        if not pd.isna(val):
                            current_fcf = float(val)
                            break

                shares_outstanding = info.get("sharesOutstanding")
                raw_growth = info.get("earningsGrowth") or info.get("revenueGrowth") or 0.10

                # yfinance sometimes returns values as whole-number percentages
                # instead of decimal fractions (e.g. 27.636 instead of 0.27636).
                # Anything > 1.0 is clearly a percentage — divide by 100 first.
                if abs(raw_growth) > 1.0:
                    raw_growth = raw_growth / 100.0

                # Safety cap: realistic compounded growth bounds
                growth_rate = max(-0.30, min(0.60, raw_growth))

                if not shares_outstanding or current_fcf is None or current_fcf <= 0:
                    raise ValueError(
                        f"Insufficient data: FCF={current_fcf}, Shares={shares_outstanding}"
                    )

                # Save to cache (valid for 90 days by default)
                self.cache.set(
                    ticker_symbol,
                    {
                        "fcf": current_fcf,
                        "shares_outstanding": shares_outstanding,
                        "growth_rate": growth_rate,
                    },
                )

            except Exception as e:
                raise ValueError(f"Fundamental fetch failed for {ticker_symbol}: {e}")

        # Apply EM adjustment if any
        required_return += em_adjustment

        # Allow caller to override the growth rate (e.g. conservative scenario)
        if growth_stage2_rate is not None:
            growth_rate = growth_stage2_rate

        # 2. Project Future Cash Flows (Stage 1)
        projected_fcfs = []
        for i in range(1, projection_years + 1):
            future_fcf = current_fcf * ((1 + growth_rate) ** i)
            projected_fcfs.append(future_fcf)

        # 3. Discount to Present Value
        pv_fcfs = [
            fcf / ((1 + required_return) ** (i + 1))
            for i, fcf in enumerate(projected_fcfs)
        ]

        # 4. Terminal Value (Gordon Growth Model)
        last_fcf = projected_fcfs[-1]
        terminal_value = (last_fcf * (1 + perpetual_growth)) / (
            required_return - perpetual_growth
        )
        pv_terminal_value = terminal_value / ((1 + required_return) ** projection_years)

        # 5. Enterprise Value → Fair Value per Share
        enterprise_value = sum(pv_fcfs) + pv_terminal_value
        fair_value = enterprise_value / shares_outstanding

        return round(float(fair_value), 2)

    def get_valuation_metrics(
        self,
        ticker_symbol: str,
        required_return: float = 0.09,
        perpetual_growth: float = 0.025,
        projection_years: int = 5,
        conservative_growth: Optional[float] = None,
    ) -> dict:
        """
        Returns a full valuation snapshot including a bull/bear range.

        Parameters
        ----------
        conservative_growth : If set, also calculates a bear-case fair value using this
                              lower growth rate, giving a tighter valuation range.
        """
        from trading.valuation.sector_data import get_em_risk_adjustment
        
        # Apply automatic Emerging Market risk premium
        orig_required_return = required_return
        em_adj = get_em_risk_adjustment(ticker_symbol)
        required_return += em_adj
        
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

            # --- Bull-case (base) DCF ---
            fair_value_bull = self.calculate_dcf_fair_value(
                ticker_symbol,
                projection_years=projection_years,
                perpetual_growth=perpetual_growth,
                required_return=required_return,
                em_adjustment=em_adj,
            )

            result = {
                "ticker": ticker_symbol,
                "current_price": round(current_price, 2),
                "fair_value_bull": fair_value_bull,
                "required_return_pct": round(required_return * 100, 1),
                "em_risk_adj_pct": round(em_adj * 100, 1) if em_adj > 0 else 0,
                "perpetual_growth_pct": round(perpetual_growth * 100, 1),
                "projection_years": projection_years,
            }

            # --- Bear-case DCF (tighter bounds) ---
            if conservative_growth is not None:
                fair_value_bear = self.calculate_dcf_fair_value(
                    ticker_symbol,
                    projection_years=projection_years,
                    perpetual_growth=perpetual_growth,
                    required_return=required_return,
                    growth_stage2_rate=conservative_growth,
                    em_adjustment=em_adj,
                )
                result["fair_value_bear"] = fair_value_bear
                result["conservative_growth_pct"] = round(conservative_growth * 100, 1)
                # Mid-point as central estimate
                result["fair_value_mid"] = round(
                    (fair_value_bull + fair_value_bear) / 2, 2
                )

            # Upside based on the most conservative estimate available
            best_estimate = result.get("fair_value_mid", fair_value_bull)
            upside = (best_estimate - current_price) / current_price
            result["upside_pct"] = round(upside * 100, 2)
            result["is_undervalued"] = upside > 0.20  # 20% margin of safety

            return result

        except Exception as e:
            return {"ticker": ticker_symbol, "error": str(e)}
