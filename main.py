"""CLI entry point for the stock trading algorithm."""

import argparse
import sys

import yaml

from trading.strategy import get_strategy
from trading.backtesting.engine import BacktestEngine
from trading.paper_trading.trader import PaperTrader
from trading.visualization.dashboard import Dashboard
from trading.scanner.engine import MarketScanner
from trading.scanner.aex_list import AEX_TICKERS
from trading.scanner.sp500_list import SP500_TICKERS
from trading.scanner.dax_list import DAX_TICKERS
from trading.scanner.nasdaq_list import NASDAQ_TICKERS
from trading.scanner.ftse_list import FTSE_TICKERS
from trading.valuation import get_valuation_engine


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
    strategy.update_valuation(ticker)
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


def cmd_scan(args, config):
    """Scan an index for signals."""
    # Override config settings if flags are provided
    if args.engine:
        config["strategy"]["valuation_engine"] = args.engine
    
    # We pass these through via the config so the strategy/engine pick them up
    if hasattr(args, 'required_return') and args.required_return is not None:
        config["strategy"]["required_return"] = args.required_return
    if hasattr(args, 'perpetual_growth') and args.perpetual_growth is not None:
        config["strategy"]["perpetual_growth"] = args.perpetual_growth
        
    scanner = MarketScanner(config)
    
    if args.index == "AEX":
        tickers = AEX_TICKERS
    elif args.index == "SP500":
        tickers = SP500_TICKERS
    elif args.index == "DAX":
        tickers = DAX_TICKERS
    elif args.index == "NASDAQ":
        tickers = NASDAQ_TICKERS
    elif args.index == "FTSE":
        tickers = FTSE_TICKERS
    else:
        tickers = args.tickers or AEX_TICKERS

    results = scanner.scan(tickers)
    scanner.print_report(results)


def cmd_valuation(args, config):
    """Run a fair-value estimate for a single ticker."""
    engine = get_valuation_engine(args.engine, sleep_seconds=args.sleep)
    print(f"\nFetching valuation for {args.ticker} [{args.engine.upper()} engine]...")
    if args.engine not in ['revenue', 'ebitda']:
        print(f"  Terminal growth: {args.perpetual_growth * 100:.2f}%")
    if hasattr(args, 'required_return') and args.required_return is not None:
        print(f"  Discount rate  : {args.required_return * 100:.1f}% (override)")
    if args.conservative_growth is not None:
        print(f"  Bear-case growth: {args.conservative_growth * 100:.1f}%")
    if hasattr(args, 'base_multiple') and args.base_multiple is not None:
        print(f"  Base P/S mult  : {args.base_multiple:.1f}x (override)")
    print()

    # Build keyword args per engine type
    kwargs = dict(
        ticker_symbol=args.ticker,
        conservative_growth=args.conservative_growth,
    )

    if args.engine == 'classic':
        kwargs['perpetual_growth'] = args.perpetual_growth
        kwargs['required_return'] = args.required_return if args.required_return is not None else 0.09
        kwargs['projection_years'] = args.projection_years
    elif args.engine == 'growth':
        kwargs['perpetual_growth'] = args.perpetual_growth
        kwargs['discount_rate_override'] = args.required_return  # None means auto-CAPM
        kwargs['stage1_years'] = args.stage1_years
        kwargs['stage2_years'] = args.stage2_years
    elif args.engine in ['revenue', 'ebitda']:
        kwargs['base_multiple_override'] = getattr(args, 'base_multiple', None)

    result = engine.get_valuation_metrics(**kwargs)

    if "error" in result:
        print(f"  ERROR: {result['error']}")
        return

    print(f"  Ticker         : {result['ticker']}")
    print(f"  Current Price  : {result['current_price']:>10.2f}")
    if result.get('engine') == 'growth':
        print(f"  Growth Rate    : {result.get('growth_rate_pct', 'N/A'):>9.1f}%")
        src = result.get('growth_rate_source', 'N/A')
        print(f"  Growth Source  : {src}")
        print(f"  Beta / CAPM    : {result.get('beta', 'N/A')} / {result.get('capm_rate_pct', 'N/A')}%")
    elif result.get('engine') == 'revenue':
        print(f"  Sector         : {result.get('sector', 'N/A')}")
        print(f"  Growth Rate    : {result.get('growth_rate_pct', 'N/A'):>9.1f}%")
        rev = result.get('trailing_revenue', 0)
        print(f"  Trailing Rev   : {rev:>14,.0f}")
        print(f"  P/S Multiple   : {result.get('ps_multiple_used', 'N/A'):>9.2f}x")
    elif result.get('engine') == 'ebitda':
        print(f"  Sector         : {result.get('sector', 'N/A')}")
        print(f"  Growth Rate    : {result.get('growth_rate_pct', 'N/A'):>9.1f}%")
        ebitda = result.get('trailing_ebitda', 0)
        print(f"  EBITDA         : {ebitda:>14,.0f}")
        print(f"  EV/EBITDA      : {result.get('ev_ebitda_multiple_used', 'N/A'):>9.2f}x")
    print(f"  Fair Value Bull: {result['fair_value_bull']:>10.2f}")
    if 'fair_value_bear' in result:
        print(f"  Fair Value Bear: {result['fair_value_bear']:>10.2f}")
        print(f"  Fair Value Mid : {result['fair_value_mid']:>10.2f}")
    print(f"  Upside %       : {result['upside_pct']:>+10.1f}%")
    status = "UNDERVALUED" if result['is_undervalued'] else "FAIRLY / OVER valued"
    print(f"  Status         : {status}")

    # --- Sensitivity Analysis ---
    if getattr(args, 'sensitivity', False):
        from trading.valuation.sensitivity import SensitivityAnalysis
        sector = result.get('sector')
        sa = SensitivityAnalysis(engine, n_simulations=args.simulations)
        sa_result = sa.run(args.ticker, sector=sector)
        sa.print_report(sa_result)


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

    # Scan subcommand
    scan_parser = subparsers.add_parser("scan", help="Scan multiple tickers for signals")
    scan_parser.add_argument("--index", type=str, default="AEX", help="Index to scan (default: AEX)")
    scan_parser.add_argument("--tickers", nargs="+", default=None, help="Specific tickers to scan")
    scan_parser.add_argument("--engine", type=str, choices=["classic", "growth", "revenue", "ebitda"],
                            help="Valuation engine to use (default: from config)")
    scan_parser.add_argument("--required-return", type=float, default=None,
                            help="Override discount rate for all stocks in the scan")
    scan_parser.add_argument("--perpetual-growth", type=float, default=None,
                            help="Override terminal growth rate for all stocks")

    # Valuation subcommand
    val_parser = subparsers.add_parser("valuation", help="DCF fair-value estimate for a ticker")
    val_parser.add_argument("--ticker", type=str, required=True, help="Ticker symbol, e.g. ADYEN.AS")
    val_parser.add_argument("--engine", type=str, default="classic", choices=["classic", "growth", "revenue", "ebitda"],
                            help="Valuation engine: 'classic' | 'growth' | 'revenue' | 'ebitda' (default: classic)")
    val_parser.add_argument("--required-return", type=float, default=None,
                            help="Override discount rate (default: CAPM for growth, 9%% for classic)")
    val_parser.add_argument("--perpetual-growth", type=float, default=0.025,
                            help="Terminal growth rate (default: 0.025 = 2.5%%)")
    val_parser.add_argument("--projection-years", type=int, default=5,
                            help="[classic only] Explicit projection horizon (default: 5)")
    val_parser.add_argument("--stage1-years", type=int, default=5,
                            help="[growth only] High-growth phase length (default: 5)")
    val_parser.add_argument("--stage2-years", type=int, default=5,
                            help="[growth only] Decay phase length (default: 5 → 10yr total)")
    val_parser.add_argument("--conservative-growth", type=float, default=None,
                            help="Bear-case growth override, e.g. 0.05 (optional)")
    val_parser.add_argument("--sleep", type=float, default=1.5,
                            help="Seconds to sleep between Yahoo Finance calls (default: 1.5)")
    val_parser.add_argument("--base-multiple", type=float, default=None,
                            help="[revenue only] Override base P/S multiple")
    val_parser.add_argument("--forward-weight", type=float, default=None,
                            help="[growth only] Forward/historical blend weight 0-1 (default: 0.6)")
    val_parser.add_argument("--sensitivity", action="store_true",
                            help="Run Monte Carlo sensitivity analysis after valuation")
    val_parser.add_argument("--simulations", type=int, default=1000,
                            help="Number of Monte Carlo simulations (default: 1000)")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "backtest":
        cmd_backtest(args, config)
    elif args.command == "paper":
        cmd_paper(args, config)
    elif args.command == "scan":
        cmd_scan(args, config)
    elif args.command == "valuation":
        cmd_valuation(args, config)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
