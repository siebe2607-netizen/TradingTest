"""Tests for strategy logic."""

import pandas as pd
import pytest
from trading.strategy.sma_rsi_macd import SmaRsiMacdStrategy
from trading.strategy.base import Signal


@pytest.fixture
def strategy_config():
    return {
        "strategy": {
            "sma_short_period": 5,
            "sma_long_period": 10,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "bollinger_period": 20,
            "bollinger_std_dev": 2,
        }
    }


def test_generate_signal_hold_initially(strategy_config):
    strategy = SmaRsiMacdStrategy(strategy_config)
    df = pd.DataFrame({"Close": [100.0]})
    # Not enough data for indicators
    assert strategy.generate_signal(df, 0) == Signal.HOLD


def test_signal_enum_values():
    assert Signal.BUY.value == 1
    assert Signal.SELL.value == -1
    assert Signal.HOLD.value == 0
