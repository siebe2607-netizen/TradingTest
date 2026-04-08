"""Risk management logic for position sizing and capital protection."""

from typing import Optional
from trading.strategy.base import Trade


class RiskManager:
    """Handles risk controls and position sizing."""

    def __init__(self, config: dict):
        self.config = config["risk"]
        self.initial_capital = self.config["initial_capital"]
        self.current_capital = self.initial_capital
        self.max_drawdown = 0.0
        self.peak_capital = self.initial_capital

    def calculate_position_size(self, price: float, available_capital: float) -> float:
        """Calculate how many shares to buy based on risk limits."""
        # Limit per-trade capital based on max_position_pct
        max_capital_per_trade = self.initial_capital * self.config["max_position_pct"]
        capital_to_use = min(available_capital, max_capital_per_trade)

        if price <= 0:
            return 0.0

        return int(capital_to_use / price)

    def should_exit(self, trade: Trade, current_price: float) -> Optional[str]:
        """Check if a trade should be closed due to risk limits (SL/TP)."""
        if not trade.is_open:
            return None

        price_change_pct = (current_price - trade.entry_price) / trade.entry_price

        # Stop Loss
        if price_change_pct <= -self.config["stop_loss_pct"]:
            return "Stop Loss"

        # Take Profit
        if price_change_pct >= self.config["take_profit_pct"]:
            return "Take Profit"

        return None

    def update_drawdown(self, portfolio_value: float) -> bool:
        """Update drawdown tracking and check if max drawdown exceeded.

        Returns:
            True if max drawdown is exceeded, False otherwise.
        """
        if portfolio_value > self.peak_capital:
            self.peak_capital = portfolio_value

        drawdown = (self.peak_capital - portfolio_value) / self.peak_capital
        self.max_drawdown = max(self.max_drawdown, drawdown)

        return drawdown >= self.config["max_drawdown_pct"]
