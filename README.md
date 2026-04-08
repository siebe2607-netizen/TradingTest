# Stock Trading Algorithm

A Python-based stock trading algorithm using technical analysis indicators with backtesting, paper trading, risk management, and visualization.

## Features

- **Technical Analysis Strategy**: Combines SMA crossover, RSI, MACD, and Bollinger Bands for signal generation
- **Backtesting Engine**: Test strategies against historical data with detailed performance metrics
- **Paper Trading**: Simulate live trading with real-time Yahoo Finance data (no real money)
- **Risk Management**: Stop-loss, take-profit, position sizing, and max drawdown controls
- **Visualization Dashboard**: 4-panel charts with price/signals, RSI, MACD, and equity curve

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Backtest

Run a backtest on historical data:

```bash
# Default: AAPL, 2 years of data
python main.py backtest

# Custom ticker and period
python main.py backtest --ticker MSFT --period 1y

# Custom date range
python main.py backtest --ticker GOOGL --start 2023-01-01 --end 2024-01-01

# Save chart to specific file
python main.py backtest --ticker AAPL --output results.png
```

### Paper Trade

Simulate live trading (no real money):

```bash
# Default tickers from config
python main.py paper

# Custom tickers
python main.py paper --tickers AAPL MSFT GOOGL
```

Press `Ctrl+C` to stop and see the session summary.

## Configuration

Edit `config.yaml` to tune strategy parameters:

```yaml
strategy:
  sma_short_period: 20    # Short-term SMA window
  sma_long_period: 50     # Long-term SMA window
  rsi_period: 14          # RSI lookback period
  rsi_overbought: 70      # RSI overbought threshold
  rsi_oversold: 30        # RSI oversold threshold

risk:
  initial_capital: 100000 # Starting capital ($)
  stop_loss_pct: 0.05     # 5% stop-loss
  take_profit_pct: 0.15   # 15% take-profit
  max_drawdown_pct: 0.20  # Halt at 20% drawdown
  max_position_pct: 0.10  # Max 10% of portfolio per position
```

## Strategy Logic

**BUY** when all conditions are met:
1. SMA short crosses above SMA long (golden cross)
2. RSI is below the overbought threshold
3. MACD histogram is positive
4. Price is above the lower Bollinger Band

**SELL** when any condition is met:
1. SMA short crosses below SMA long (death cross)
2. RSI exceeds the overbought threshold
3. MACD histogram flips from positive to negative

## Adding a New Strategy

1. Create a new file in `trading/strategy/`
2. Subclass `BaseStrategy` from `trading/strategy/base.py`
3. Implement `prepare_data()` and `generate_signal()`
4. Register it in `trading/strategy/__init__.py`

## Project Structure

```
trading/
  data/fetcher.py          - Yahoo Finance data retrieval
  indicators/technical.py  - SMA, EMA, RSI, MACD, Bollinger Bands
  strategy/base.py         - Abstract strategy interface
  strategy/sma_rsi_macd.py - Default technical analysis strategy
  risk/manager.py          - Position sizing & risk controls
  backtesting/engine.py    - Historical simulation engine
  paper_trading/trader.py  - Live paper trading loop
  visualization/dashboard.py - Matplotlib charts
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Disclaimer

This software is for educational and research purposes only. It is not financial advice. Do not use this for actual trading without thorough testing and understanding of the risks involved. Past performance does not guarantee future results.
