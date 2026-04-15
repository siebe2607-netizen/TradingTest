import yfinance as yf
import pandas as pd
from trading.strategy.sma_rsi_macd import SmaRsiMacdStrategy

config = {
    "strategy": {
        "sma_short_period": 20,
        "sma_long_period": 50,
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "ema_period": 12,
        "macdsignal": 9,
        "macd_fast": 12,
        "macd_slow": 26
    }
}

def debug_signals(tickers):
    strategy = SmaRsiMacdStrategy(config)
    for ticker in tickers:
        print(f"\n--- Debugging {ticker} ---")
        try:
            df = yf.download(ticker, period="1y", progress=False)
            df = strategy.prepare_data(df)
            
            last_row = df.iloc[-1]
            print(f"Price: {last_row['Close']:.2f}")
            print(f"SMA20: {last_row['SMA20']:.2f}, SMA50: {last_row['SMA50']:.2f} -> {'PASS' if last_row['SMA20'] > last_row['SMA50'] else 'FAIL'}")
            print(f"RSI: {last_row['RSI']:.2f} -> {'PASS' if last_row['RSI'] < 70 else 'FAIL'}")
            print(f"MACD: {last_row['MACD']:.2f}, Signal: {last_row['MACDSignal']:.2f} -> {'PASS' if last_row['MACD'] > last_row['MACDSignal'] else 'FAIL'}")
            
            sig = strategy.generate_signal(df, len(df)-1)
            print(f"RESULT: {sig.name}")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    debug_signals(["NVDA", "MSFT", "AAPL", "META"])
