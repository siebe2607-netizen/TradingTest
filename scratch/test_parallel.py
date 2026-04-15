import concurrent.futures
import yfinance as yf
import time

tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "BRK-B", "JNJ", "V"]

def fetch_one(ticker):
    tk = yf.Ticker(ticker)
    return tk.fast_info.get('lastPrice')

def test_sequential():
    start = time.time()
    for t in tickers:
        fetch_one(t)
    return time.time() - start

def test_parallel():
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(fetch_one, tickers))
    return time.time() - start

if __name__ == "__main__":
    s_time = test_sequential()
    p_time = test_parallel()
    print(f"Sequential: {s_time:.2f}s")
    print(f"Parallel: {p_time:.2f}s")
    print(f"Speedup: {s_time/p_time:.2f}x")
