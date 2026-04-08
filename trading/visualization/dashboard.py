"""Visualization dashboard for backtest results."""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


class Dashboard:
    """Generates charts and prints metrics for backtests."""

    def __init__(self, result):
        self.res = result

    def print_metrics(self):
        """Print detailed performance statistics to console."""
        print("\n" + "=" * 40)
        print(f" PERFORMANCE SUMMARY: {self.res.ticker} ")
        print("=" * 40)
        print(f"Initial Capital:  ${self.res.initial_capital:,.2f}")
        print(f"Final Capital:    ${self.res.final_capital:,.2f}")
        print(f"Total Return:     {self.res.total_return_pct:.2%}")
        print(f"Max Drawdown:     {self.res.max_drawdown_pct:.2%}")
        print(f"Total Trades:     {len(self.res.trades)}")
        print(f"Win Rate:         {self.res.win_rate:.2%}")
        
        if self.res.fair_value:
            print(f"Fair Value Est:   ${self.res.fair_value:,.2f}")
            latest_price = self.res.df["Close"].iloc[-1]
            upside = (self.res.fair_value - latest_price) / latest_price
            print(f"Upside/Downside:  {upside:.2%}")

        if self.res.trades:
            returns = [t.pct_return for t in self.res.trades]
            avg_return = np.mean(returns)
            best_trade = max(returns)
            worst_trade = min(returns)
            print(f"Avg trade:        {avg_return:.2%}")
            print(f"Best trade:       {best_trade:.2%}")
            print(f"Worst trade:      {worst_trade:.2%}")
        print("=" * 40)

    def plot_all(self, save_path=None):
        """Create a 4-panel dashboard of the backtest."""
        fig, axes = plt.subplots(4, 1, figsize=(14, 18), sharex=True, gridspec_kw={"height_ratios": [3, 1, 1, 1.5]})
        df = self.res.df

        # 1. Price and Strategy Signals
        ax0 = axes[0]
        ax0.plot(df.index, df["Close"], label="Price", color="black", alpha=0.7)
        if "BB_Upper" in df.columns:
            ax0.fill_between(df.index, df["BB_Lower"], df["BB_Upper"], color="gray", alpha=0.2, label="Bollinger Bands")

        if self.res.fair_value:
            ax0.axhline(self.res.fair_value, color="darkblue", linestyle="--", linewidth=2, label=f"Fair Value (${self.res.fair_value:,.2f})")

        # Plot Strategy Signals
        buys = [t for t in self.res.trades]
        buy_dates = [t.entry_date for t in buys]
        buy_prices = [t.entry_price for t in buys]
        sell_dates = [t.exit_date for t in buys if t.exit_date is not None]
        sell_prices = [t.exit_price for t in buys if t.exit_price is not None]

        ax0.scatter(buy_dates, buy_prices, marker="^", color="green", s=100, label="BUY", zorder=5)
        ax0.scatter(sell_dates, sell_prices, marker="v", color="red", s=100, label="SELL", zorder=5)

        ax0.set_title(f"{self.res.ticker} Trading Signals", fontsize=16)
        ax0.legend(loc="upper left")
        ax0.grid(True, alpha=0.3)

        # 2. RSI
        ax1 = axes[1]
        ax1.plot(df.index, df["RSI"], color="purple", label="RSI")
        ax1.axhline(70, color="red", linestyle="--", alpha=0.5)
        ax1.axhline(30, color="green", linestyle="--", alpha=0.5)
        ax1.set_ylabel("RSI")
        ax1.set_ylim(0, 100)
        ax1.grid(True, alpha=0.3)

        # 3. MACD
        ax2 = axes[2]
        colors = ["green" if x > 0 else "red" for x in df["MACD_Hist"]]
        ax2.bar(df.index, df["MACD_Hist"], color=colors, alpha=0.5, label="MACD Hist")
        ax2.plot(df.index, df["MACD"], color="blue", label="MACD")
        ax2.plot(df.index, df["MACD_Signal"], color="orange", label="Signal")
        ax2.set_ylabel("MACD")
        ax2.legend(loc="upper left")
        ax2.grid(True, alpha=0.3)

        # 4. Equity Curve
        ax3 = axes[3]
        ax3.plot(self.res.equity_curve.index, self.res.equity_curve.values, color="darkgreen", linewidth=2)
        ax3.fill_between(self.res.equity_curve.index, self.res.initial_capital, self.res.equity_curve.values, color="green", alpha=0.1)
        ax3.set_title("Equity Curve ($)", fontsize=14)
        ax3.set_ylabel("Value")
        ax3.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path)
            print(f"Chart saved to {save_path}")
        else:
            plt.show()

    def plot_trade_distribution(self):
        """Plot a histogram of trade returns."""
        if not self.res.trades:
            return

        returns = [t.pct_return * 100 for t in self.res.trades]
        plt.figure(figsize=(10, 6))
        plt.hist(returns, bins=20, color="skyblue", edgecolor="black")
        plt.axvline(0, color="red", linestyle="--")
        plt.title(f"Trade Return Distribution - {self.res.ticker}")
        plt.xlabel("Return %")
        plt.ylabel("Frequency")
        plt.grid(True, alpha=0.3)
        plt.show()
