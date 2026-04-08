"""Technical analysis indicators implemented with pandas/numpy."""

import numpy as np
import pandas as pd


def add_sma(df: pd.DataFrame, period: int, column: str = "Close") -> pd.DataFrame:
    """Add Simple Moving Average column."""
    df[f"SMA_{period}"] = df[column].rolling(window=period).mean()
    return df


def add_ema(df: pd.DataFrame, period: int, column: str = "Close") -> pd.DataFrame:
    """Add Exponential Moving Average column."""
    df[f"EMA_{period}"] = df[column].ewm(span=period, adjust=False).mean()
    return df


def add_rsi(df: pd.DataFrame, period: int = 14, column: str = "Close") -> pd.DataFrame:
    """Add Relative Strength Index column."""
    delta = df[column].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = "Close",
) -> pd.DataFrame:
    """Add MACD, MACD_Signal, and MACD_Hist columns."""
    ema_fast = df[column].ewm(span=fast, adjust=False).mean()
    ema_slow = df[column].ewm(span=slow, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    return df


def add_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    column: str = "Close",
) -> pd.DataFrame:
    """Add Bollinger Band columns (Upper, Middle, Lower)."""
    sma = df[column].rolling(window=period).mean()
    std = df[column].rolling(window=period).std()
    df["BB_Upper"] = sma + (std_dev * std)
    df["BB_Middle"] = sma
    df["BB_Lower"] = sma - (std_dev * std)
    return df


def add_all_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Apply all indicators based on config parameters."""
    cfg = config["strategy"]
    df = add_sma(df, cfg["sma_short_period"])
    df = add_sma(df, cfg["sma_long_period"])
    df = add_ema(df, cfg["ema_period"])
    df = add_rsi(df, cfg["rsi_period"])
    df = add_macd(df, cfg["macd_fast"], cfg["macd_slow"], cfg["macd_signal"])
    df = add_bollinger_bands(df, cfg["bollinger_period"], cfg["bollinger_std_dev"])
    return df
