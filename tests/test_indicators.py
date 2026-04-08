"""Tests for technical indicators."""

import pandas as pd
import numpy as np
import pytest
from trading.indicators import technical


@pytest.fixture
def sample_data():
    """Create a sample price dataframe."""
    dates = pd.date_range(start="2023-01-01", periods=100)
    data = {"Close": np.linspace(100, 200, 100)}  # Linear uptrend
    return pd.DataFrame(data, index=dates)


def test_sma(sample_data):
    period = 10
    df = technical.add_sma(sample_data, period)
    col_name = f"SMA_{period}"
    assert col_name in df.columns
    assert pd.isna(df[col_name].iloc[period - 2])
    assert not pd.isna(df[col_name].iloc[period - 1])
    # For 100 values from 100 to 200, step is 100/99. 
    # Average of first 10 is 100 + 4.5 * (100/99) = 104.5454...
    assert df[col_name].iloc[period - 1] == pytest.approx(104.5454, rel=1e-4)


def test_rsi(sample_data):
    df = technical.add_rsi(sample_data, period=14)
    assert "RSI" in df.columns
    # Linear uptrend should have RSI > 50 (actually 100 for steady gains)
    assert df["RSI"].iloc[-1] > 50


def test_macd(sample_data):
    df = technical.add_macd(sample_data)
    assert "MACD" in df.columns
    assert "MACD_Signal" in df.columns
    assert "MACD_Hist" in df.columns


def test_bollinger_bands(sample_data):
    df = technical.add_bollinger_bands(sample_data, period=20)
    assert "BB_Upper" in df.columns
    assert "BB_Lower" in df.columns
    assert df["BB_Upper"].iloc[-1] > df["BB_Lower"].iloc[-1]
