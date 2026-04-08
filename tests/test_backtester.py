"""Tests for backtesting engine."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from trading.backtesting.engine import BacktestEngine


@pytest.fixture
def config():
    return {
        "strategy": {"name": "sma_rsi_macd"},
        "risk": {
            "initial_capital": 100000.0,
            "max_position_pct": 0.1,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.15,
            "max_drawdown_pct": 0.2,
        },
    }


def test_backtest_summary_calculation(config):
    engine = BacktestEngine(config)
    ticker = "AAPL"
    df = pd.DataFrame({"Close": [100, 110]})
    equity = pd.Series([100000, 110000])

    # Mock components to just test _summarize
    risk_mgr = MagicMock()
    risk_mgr.initial_capital = 100000.0
    risk_mgr.max_drawdown = 0.05

    result = engine._summarize(ticker, df, [], equity, risk_mgr)

    assert result.ticker == ticker
    assert result.initial_capital == 100000.0
    assert result.final_capital == 110000.0
    assert result.total_return_pct == pytest.approx(0.1)
    assert result.win_rate == 0.0
