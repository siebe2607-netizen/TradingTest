import pandas as pd
import numpy as np
import concurrent.futures
from typing import Union
from tqdm import tqdm

from trading.data.fetcher import DataFetcher
from trading.strategy.valuation_overlay import ValuationOverlayStrategy
from trading.strategy.base import Signal

def _scan_single_ticker_task(ticker, config):
    """Standalone task for process-based scanning (to avoid shared state)."""
    import time
    import random
    fetcher = DataFetcher()
    strategy = ValuationOverlayStrategy(config)
    try:
        # Avoid aggressive rate limiting by staggering starts
        time.sleep(random.uniform(0.1, 0.5))
        
        # 1. Fetch recent data
        df = fetcher.fetch_latest(ticker, period="1y")
        df = strategy.prepare_data(df)

        # 2. Update valuation
        strategy.update_valuation(ticker)

        # 3. Generate signal for latest bar
        signal = strategy.generate_signal(df, len(df) - 1)
        
        # 4. Collect results
        current_price = df["Close"].iloc[-1]
        fair_value = strategy.fair_value
        upside = ((fair_value - current_price) / current_price) if fair_value else 0

        return {
            "Ticker": ticker,
            "Price": round(float(current_price), 2),
            "Fair Value": round(float(fair_value), 2) if fair_value else "N/A",
            "Upside %": round(float(upside * 100), 2) if fair_value else "N/A",
            "Signal": signal.name,
            "Status": "Actionable" if signal != Signal.HOLD else "Stable"
        }

    except Exception as e:
        return {
            "Ticker": ticker,
            "Price": "Error",
            "Fair Value": "N/A",
            "Upside %": "N/A",
            "Signal": "ERROR",
            "Status": str(e)[:40]
        }

class MarketScanner:
    """Scans a list of tickers for active strategy signals in parallel."""

    def __init__(self, config: dict, max_workers: int = 3):
        self.config = config
        self.max_workers = max_workers

    def scan(self, tickers: list[str]) -> list[dict]:
        """
        Scan a list of tickers in parallel using processes to ensure isolation.
        """
        results = []
        print(f"Scanning {len(tickers)} tickers using {self.max_workers} processes...")

        with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Wrap with tqdm for progress bar
            futures = [executor.submit(_scan_single_ticker_task, ticker, self.config) for ticker in tickers]
            
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(tickers)):
                results.append(future.result())

        return results

    def print_report(self, results: list[dict], top_n: int = 50):
        """Print a formatted table of the scan results."""
        df_results = pd.DataFrame(results)
        
        # Convert Upside % to numeric for sorting, replacing N/A with NaN
        df_results["Upside %"] = pd.to_numeric(df_results["Upside %"].replace("N/A", np.nan))
        
        # Highlight BUY signals
        buys = df_results[df_results["Signal"] == "BUY"]
        
        print("\n" + "=" * 80)
        print(" MARKET SCAN REPORT ")
        print("=" * 80)
        
        if not buys.empty:
            print(f"Found {len(buys)} active BUY signals:")
            print(buys.to_string(index=False))
            print("-" * 80)

        # Show Top N by upside potential
        print(f"\nTop {top_n} Tickers by Upside Potential:")
        report_df = df_results.sort_values(by="Upside %", ascending=False).head(top_n)
        print(report_df.to_string(index=False))
        print("=" * 80)
