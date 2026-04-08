"""Tests for risk management logic."""

import pytest
from trading.risk.manager import RiskManager
from trading.strategy.base import Trade
import pandas as pd


@pytest.fixture
def risk_config():
    return {
        "risk": {
            "initial_capital": 100000.0,
            "max_position_pct": 0.1,  # $10k per trade
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.15,
            "max_drawdown_pct": 0.2,
        }
    }


def test_position_sizing(risk_config):
    rm = RiskManager(risk_config)
    # Price $100, Capital $100k -> 10% of $100k is $10k. $10k / $100 = 100 shares.
    size = rm.calculate_position_size(price=100.0, available_capital=100000.0)
    assert size == 100


def test_stop_loss_trigger(risk_config):
    rm = RiskManager(risk_config)
    trade = Trade(ticker="AAPL", entry_date=pd.Timestamp.now(), entry_price=100.0, quantity=10)

    # 5% SL -> trigger at $95 or below
    assert rm.should_exit(trade, 96.0) is None
    assert rm.should_exit(trade, 95.0) == "Stop Loss"
    assert rm.should_exit(trade, 90.0) == "Stop Loss"


def test_take_profit_trigger(risk_config):
    rm = RiskManager(risk_config)
    trade = Trade(ticker="AAPL", entry_date=pd.Timestamp.now(), entry_price=100.0, quantity=10)

    # 15% TP -> trigger at $115 or above
    assert rm.should_exit(trade, 110.0) is None
    assert rm.should_exit(trade, 115.0) == "Take Profit"
    assert rm.should_exit(trade, 120.0) == "Take Profit"


def test_drawdown_limit(risk_config):
    rm = RiskManager(risk_config)
    # Peak starts at $100k. Max drawdown 20% -> Halt at $80k.
    assert rm.update_drawdown(90000.0) is False
    assert rm.update_drawdown(80000.0) is True
