import yfinance as yf
import time

tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]

def test_fetch(ticker_sym):
    print(f"\n--- Testing {ticker_sym} ---")
    tk = yf.Ticker(ticker_sym)
    
    start = time.time()
    try:
        print("Fetching info...")
        # info is notorious for being slow/failing
        info = tk.info
        print(f"Info keys received: {len(info) if info else 0}")
        
        print("Fetching cashflow...")
        cf = tk.cashflow
        print(f"Cashflow shape: {cf.shape if not cf.empty else 'EMPTY'}")
        
        print(f"Duration: {time.time() - start:.2f}s")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    for t in tickers:
        test_fetch(t)
