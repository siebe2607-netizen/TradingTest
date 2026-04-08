"""Live paper trading loop using scheduled execution."""

import time
import schedule
import pytz
from datetime import datetime
from typing import Dict, List, Optional

from trading.data.fetcher import DataFetcher
from trading.strategy import get_strategy, Signal, Trade
from trading.risk.manager import RiskManager


class PaperTrader:
    """Simulates live trading in a real-time loop."""

    def __init__(self, config: dict):
        self.config = config
        self.fetcher = DataFetcher()
        self.risk_mgr = RiskManager(config)
        self.strategy = get_strategy(config["strategy"]["name"], config)

        self.tickers = config["paper_trading"]["tickers"]
        self.cash = self.config["risk"]["initial_capital"]
        self.positions: Dict[str, Trade] = {}
        self.trade_history: List[Trade] = []

        self.tz = pytz.timezone(config["paper_trading"]["timezone"])

    def is_market_open(self) -> bool:
        """Check if current time is within trading hours."""
        now = datetime.now(self.tz)
        if now.weekday() >= 5:  # Weekend
            return False

        start_time = datetime.strptime(self.config["paper_trading"]["trading_hours_start"], "%H:%M").time()
        end_time = datetime.strptime(self.config["paper_trading"]["trading_hours_end"], "%H:%M").time()

        return start_time <= now.time() <= end_time

    def execute_step(self):
        """Single iteration of the trading loop."""
        if not self.is_market_open():
            return

        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking markets...")

        for ticker in self.tickers:
            try:
                self._process_ticker(ticker)
            except Exception as e:
                print(f"Error processing {ticker}: {e}")

        self._print_status()

    def _process_ticker(self, ticker: str):
        """Analyze and potentially trade a specific ticker."""
        # 1. Get data and current price
        df = self.fetcher.fetch_latest(ticker)
        df = self.strategy.prepare_data(df)
        current_price = self.fetcher.fetch_current_price(ticker)

        # 2. Check existing position for risk exits
        if ticker in self.positions:
            trade = self.positions[ticker]
            exit_reason = self.risk_mgr.should_exit(trade, current_price)

            if exit_reason:
                self._close_position(ticker, current_price, exit_reason)
                return

        # 3. Generate strategy signal
        signal = self.strategy.generate_signal(df, len(df) - 1)

        if signal == Signal.BUY and ticker not in self.positions:
            qty = self.risk_mgr.calculate_position_size(current_price, self.cash)
            if qty > 0:
                self._open_position(ticker, current_price, qty)

        elif signal == Signal.SELL and ticker in self.positions:
            self._close_position(ticker, current_price, "Strategy Signal")

    def _open_position(self, ticker: str, price: float, quantity: float):
        cost = price * quantity
        self.cash -= cost
        trade = Trade(
            ticker=ticker,
            entry_date=pd.Timestamp.now(),
            entry_price=price,
            quantity=quantity,
        )
        self.positions[ticker] = trade
        print(f"BUY {quantity} {ticker} @ {price:.2f}")

    def _close_position(self, ticker: str, price: float, reason: str):
        trade = self.positions.pop(ticker)
        trade.exit_date = pd.Timestamp.now()
        trade.exit_price = price
        trade.reason = reason
        trade.profit_loss = (price - trade.entry_price) * trade.quantity
        trade.pct_return = (price - trade.entry_price) / trade.entry_price

        self.cash += price * trade.quantity
        self.trade_history.append(trade)
        print(f"SELL {ticker} @ {price:.2f} | Reason: {reason} | Return: {trade.pct_return:.2%}")

    def _print_status(self):
        portfolio_value = self.cash + sum(p.quantity * self.fetcher.fetch_current_price(t) for t, p in self.positions.items())
        total_return = (portfolio_value - self.config["risk"]["initial_capital"]) / self.config["risk"]["initial_capital"]

        print(f"--- Status ---")
        print(f"Cash: ${self.cash:.2f}")
        print(f"Positions: {list(self.positions.keys())}")
        print(f"Portfolio Value: ${portfolio_value:.2f}")
        print(f"Total Return: {total_return:.2%}")

    def start(self):
        """Run the persistent paper trading loop."""
        print(f"Starting paper trader for {self.tickers}...")
        interval = self.config["paper_trading"]["check_interval_seconds"]

        schedule.every(interval).seconds.do(self.execute_step)

        # Run immediately on start
        self.execute_step()

        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping paper trader...")
            self._print_status()


# Mock pandas for Trade timestamp in open_position
import pandas as pd
