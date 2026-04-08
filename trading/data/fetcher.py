"""Data retrieval from Yahoo Finance."""

import yfinance as yf
import pandas as pd
from typing import Optional


class DataFetcher:
    """Fetches stock data from Yahoo Finance."""

    def fetch_historical(
        self,
        ticker: str,
        period: str = "2y",
        interval: str = "1d",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data."""
        kwargs = {"period": period, "interval": interval} if not (start and end) else {"start": start, "end": end, "interval": interval}
        df = yf.download(ticker, progress=False, group_by='ticker', **kwargs)

        if df.empty:
            raise ValueError(f"No data returned for ticker '{ticker}'")

        # Handle MultiIndex output from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            if ticker in df.columns.levels[0]:
                df = df[ticker].copy()
            else:
                df.columns = df.columns.get_level_values(1) if len(df.columns.levels) > 1 else df.columns.get_level_values(0)

        # Drop Adj Close if present, keep core OHLCV
        cols_to_keep = ["Open", "High", "Low", "Close", "Volume"]
        available_cols = [c for c in cols_to_keep if c in df.columns]
        df = df[available_cols].copy()

        df = df.dropna(subset=["Close"])
        df.index = pd.DatetimeIndex(df.index)

        return df

    def fetch_latest(self, ticker: str, period: str = "60d", interval: str = "1d") -> pd.DataFrame:
        """Fetch recent data for paper trading signal generation."""
        return self.fetch_historical(ticker, period=period, interval=interval)

    def fetch_current_price(self, ticker: str) -> float:
        """Get the most recent price for a ticker."""
        stock = yf.Ticker(ticker)
        price = stock.fast_info.get("lastPrice")
        if price is None:
            # Fallback: get last close from history
            hist = stock.history(period="1d")
            if hist.empty:
                raise ValueError(f"Cannot get current price for '{ticker}'")
            price = float(hist["Close"].iloc[-1])
        return float(price)
