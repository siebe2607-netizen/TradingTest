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
        """Fetch historical OHLCV data.

        Args:
            ticker: Stock symbol (e.g. "AAPL").
            period: Data period (e.g. "2y", "6mo"). Ignored if start/end given.
            interval: Bar interval (e.g. "1d", "1h").
            start: Start date as YYYY-MM-DD string.
            end: End date as YYYY-MM-DD string.

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume.
            Index is DatetimeIndex.

        Raises:
            ValueError: If no data is returned for the ticker.
        """
        if start and end:
            df = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
        else:
            df = yf.download(ticker, period=period, interval=interval, progress=False)

        if df.empty:
            raise ValueError(f"No data returned for ticker '{ticker}'")

        # yfinance may return MultiIndex columns for single ticker; flatten
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Drop Adj Close if present, keep core OHLCV
        if "Adj Close" in df.columns:
            df = df.drop(columns=["Adj Close"])

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
