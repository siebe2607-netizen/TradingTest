"""CLI entry point for the stock trading algorithm."""

import argparse
import sys

import yaml

from trading.strategy import get_strategy
from trading.backtesting.engine import BacktestEngine
from trading.paper_trading.trader import PaperTrader
from trading.visualization.dashboard import Dashboard


def load_config(path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def cmd_backtest(args, config):
    """Run a backtest."""
    ticker = args.ticker or config["data"]["default_ticker"]
    period = args.period or config["data"]["default_period"]

    print(f"Running backtest for {ticker}...")
    strategy = get_strategy(config["strategy"]["name"], config)
    engine = BacktestEngine(config)

    result = engine.run(
        ticker=ticker,
        strategy=strategy,
        period=period,
        start=args.start,
        end=args.end,
    )

    # Show results
    dashboard = Dashboard(result)
    dashboard.print_metrics()
    dashboard.plot_all(save_path=args.output)
    dashboard.plot_trade_distribution()

    print(f"\nBacktest complete. {len(result.trades)} trades executed.")


def cmd_paper(args, config):
    """Start paper trading."""
    if args.tickers:
        config["paper_trading"]["tickers"] = args.tickers

    trader = PaperTrader(config)
    trader.start()


def main():
    parser = argparse.ArgumentParser(
        description="Stock Trading Algorithm - Backtest, Paper Trade, and Visualize"
    )
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config file")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Backtest subcommand
    bt_parser = subparsers.add_parser("backtest", help="Run a backtest on historical data")
    bt_parser.add_argument("--ticker", type=str, default=None, help="Stock ticker (default: from config)")
    bt_parser.add_argument("--period", type=str, default=None, help="Data period, e.g. 2y, 6mo (default: from config)")
    bt_parser.add_argument("--start", type=str, default=None, help="Start date YYYY-MM-DD (overrides period)")
    bt_parser.add_argument("--end", type=str, default=None, help="End date YYYY-MM-DD (overrides period)")
    bt_parser.add_argument("--output", type=str, default=None, help="Save chart to file path")

    # Paper trading subcommand
    pt_parser = subparsers.add_parser("paper", help="Start paper trading (simulated live trading)")
    pt_parser.add_argument("--tickers", nargs="+", default=None, help="Tickers to trade (default: from config)")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "backtest":
        cmd_backtest(args, config)
    elif args.command == "paper":
        cmd_paper(args, config)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
