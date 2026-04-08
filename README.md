# Stock Trading & Valuation Algorithm

A Python-based algorithmic trading and fundamental analysis tool. This engine combines traditional technical indicators with a sophisticated Discounted Cash Flow (DCF) valuation model to find undervalued opportunities in the market.

## Key Features

- **Dual Valuation Engines**: 
  - **Classic**: A 5-year flat DCF model with a standard discount rate.
  - **Growth (CAPM)**: A 10-year model using the Capital Asset Pricing Model (CAPM) for stock-specific risk pricing, featuring growth decay and multi-stage projections.
- **Market Scanner**: Instantly scan entire indices (S&P 500, AEX) for undervalued stocks and technical buy signals.
- **Robust Data Fetching**: Advanced Yahoo Finance integration with built-in rate limiting and fallback price logic to handle market-closed/stale data.
- **Strategy Overlay**: Only executes technical trades (RSI/SMA/MACD) on stocks that are fundamentally undervalued by a configurable Margin of Safety.
- **Position & Risk Management**: Automated stop-loss, take-profit, and position sizing based on portfolio equity.
- **Visualization**: Detailed 4-panel charting of price, technicals, and equity curves.

---

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd stock_trading_algo

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Usage Guide

### 1. Market Scanning
Scan an index to find the best upside potential.
```bash
# Scan S&P 500 using the standard engine
python3 main.py scan --index SP500

# Scan AEX using the Growth (CAPM) engine
python3 main.py scan --index AEX --engine growth
```

### 2. Deep-Dive Valuation
Run a detailed DCF analysis on a specific ticker.
```bash
# Simple valuation
python3 main.py valuation --ticker ADYEN.AS

# Advanced growth valuation with a "Bear Case" scenario
python3 main.py valuation --ticker DLO --engine growth --conservative-growth 0.15
```

### 3. Backtesting
Test a strategy against historical data.
```bash
python3 main.py backtest --ticker ASML.AS --period 2y --output asml_chart.png
```

---

## 🛠 Advanced Configuration

### Valuation Engines
You can tune the fair-value math in `config.yaml` or via CLI:
- `--engine growth`: Uses a 10-year horizon. Years 1-5 use explicit growth; years 6-10 "fade" down to terminal growth. Uses **Beta** to calculate the discount rate automatically.
- `--required-return`: Override the discount rate (default is 9% for classic or CAPM-derived for growth).
- `--perpetual-growth`: The growth rate assumed forever (default: 2.5%).

### Managing Tickers
To add your own stocks to the scanner:
1. Open `trading/scanner/aex_list.py` (or create a new index file).
2. Add the Yahoo Finance ticker symbol (e.g., `NVDA`, `ADYEN.AS`) to the list.
3. Use the `--index` flag in the scan command to point to your list.

---

## 📈 Strategy Logic: Valuation Overlay
The algorithm uses the `ValuationOverlayStrategy` which only triggers a **BUY** if:
1. **Technical Signal**: SMA Golden Cross + RSI < 70 + MACD Positive.
2. **Fundamental Signal**: Current Price is at least 15% (Margin of Safety) below the Fair Value calculated by the DCF engine.

---

## Project Structure

```text
trading/
  ├── valuation/           # DCF Engines (Classic & Growth/CAPM)
  ├── scanner/             # Index scanners (S&P 500 & AEX)
  ├── strategy/            # Trading logic (Technicals + Overlays)
  ├── data/                # Robust YFinance fetchers
  ├── indicators/          # Technical math (SMA, RSI, etc.)
  └── visualization/       # Matplotlib dashboards
```

## Running Tests
```bash
export PYTHONPATH=$PYTHONPATH:.
python -m pytest tests/ -v
```

## Disclaimer
Educational purposes only. This engine does not constitute financial advice. Algorithmic trading involves high risk.
