"""Source for S&P 500 index tickers."""

import pandas as pd
import os

CACHE_FILE = "sp500_tickers.csv"

def get_sp500_tickers() -> list:
    """Fetch S&P 500 tickers from Wikipedia, using local cache if available."""
    if os.path.exists(CACHE_FILE):
        return pd.read_csv(CACHE_FILE)["Symbol"].tolist()

    print("Fetching S&P 500 tickers from GitHub source...")
    try:
        import requests
        import io
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        response = requests.get(url)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            tickers = df["Symbol"].tolist()
            
            # yfinance uses '-' instead of '.' for tickers like BRK.B
            tickers = [t.replace(".", "-") for t in tickers]
            
            # Save to cache
            pd.DataFrame({"Symbol": tickers}).to_csv(CACHE_FILE, index=False)
            return tickers
        else:
            raise Exception(f"Failed to fetch CSV: {response.status_code}")
    except Exception as e:
        print(f"Error fetching SP500 tickers: {e}")
        # Return a small fallback list if fetch fails
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "BRK-B", "V", "JNJ"]

SP500_TICKERS = get_sp500_tickers()
