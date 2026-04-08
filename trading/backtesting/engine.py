"""Engine for backtesting trading strategies against historical data."""

import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass

from trading.data.fetcher import DataFetcher
from trading.strategy.base import BaseStrategy, Signal, Trade
from trading.risk.manager import RiskManager


@dataclass
class BacktestResult:
    """Encapsulates the results of a backtest run."""

    ticker: str
    df: pd.DataFrame
    trades: List[Trade]
    equity_curve: pd.Series
    initial_capital: float
    final_capital: float
    total_return_pct: float
    max_drawdown_pct: float
    win_rate: float


class BacktestEngine:
    """Simulates trading strategy on historical price data."""

    def __init__(self, config: dict):
        self.config = config
        self.fetcher = DataFetcher()

    def run(
        self,
        ticker: str,
        strategy: BaseStrategy,
        period: str = "2y",
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> BacktestResult:
        """Execute the backtest simulation."""
        # 1. Fetch and prepare data
        df = self.fetcher.fetch_historical(ticker, period=period, start=start, end=end)
        df = strategy.prepare_data(df)

        risk_mgr = RiskManager(self.config)
        capital = risk_mgr.initial_capital
        active_trade: Optional[Trade] = None
        executed_trades: List[Trade] = []
        equity_values = []

        # 2. Iterate through time steps
        for i in range(len(df)):
            current_date = df.index[i]
            current_price = df["Close"].iloc[i]

            # Check Risk Limits if in trade
            if active_trade:
                exit_reason = risk_mgr.should_exit(active_trade, current_price)
                if exit_reason:
                    self._close_trade(active_trade, current_date, current_price, exit_reason)
                    capital += active_trade.exit_price * active_trade.quantity
                    executed_trades.append(active_trade)
                    active_trade = None

            # Generate and execute Strategy Signals
            signal = strategy.generate_signal(df, i)

            if signal == Signal.BUY and not active_trade:
                qty = risk_mgr.calculate_position_size(current_price, capital)
                if qty > 0:
                    cost = qty * current_price
                    capital -= cost
                    active_trade = Trade(
                        ticker=ticker,
                        entry_date=current_date,
                        entry_price=current_price,
                        quantity=qty,
                    )
            elif signal == Signal.SELL and active_trade:
                self._close_trade(active_trade, current_date, current_price, "Strategy Signal")
                capital += active_trade.exit_price * active_trade.quantity
                executed_trades.append(active_trade)
                active_trade = None

            # Track equity (cash + position value)
            pos_value = (active_trade.quantity * current_price) if active_trade else 0
            total_value = capital + pos_value
            equity_values.append(total_value)

            # Check for catastrophic drawdown halt
            if risk_mgr.update_drawdown(total_value):
                print(f"CRITICAL: Max drawdown exceeded at {current_date}. Halting backtest.")
                break

        # 3. Finalize
        if active_trade:
            # Force close last trade at end of data
            self._close_trade(active_trade, df.index[-1], df["Close"].iloc[-1], "End of Data")
            executed_trades.append(active_trade)

        equity_curve = pd.Series(equity_values, index=df.index[: len(equity_values)])

        return self._summarize(ticker, df, executed_trades, equity_curve, risk_mgr)

    def _close_trade(self, trade: Trade, date: pd.Timestamp, price: float, reason: str):
        """Helper to fill trade exit details."""
        trade.exit_date = date
        trade.exit_price = price
        trade.reason = reason
        trade.profit_loss = (trade.exit_price - trade.entry_price) * trade.quantity
        trade.pct_return = (trade.exit_price - trade.entry_price) / trade.entry_price

    def _summarize(
        self,
        ticker: str,
        df: pd.DataFrame,
        trades: List[Trade],
        equity: pd.Series,
        risk_mgr: RiskManager,
    ) -> BacktestResult:
        """Calculate performance metrics."""
        initial = risk_mgr.initial_capital
        final = equity.iloc[-1] if not equity.empty else initial

        total_return = (final - initial) / initial
        wins = [t for t in trades if t.profit_loss > 0]
        win_rate = len(wins) / len(trades) if trades else 0.0

        return BacktestResult(
            ticker=ticker,
            df=df,
            trades=trades,
            equity_curve=equity,
            initial_capital=initial,
            final_capital=final,
            total_return_pct=total_return,
            max_drawdown_pct=risk_mgr.max_drawdown,
            win_rate=win_rate,
        )
