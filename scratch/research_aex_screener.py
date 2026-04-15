import yfinance as yf

# Common AEX Tickers
aex_tickers = [
    "ADYEN.AS", "ASML.AS", "SHELL.AS", "UNA.AS", "HEIA.AS", 
    "PRX.AS", "INGA.AS", "AD.AS", "ABN.AS", "DSM.AS",
    "AKZA.AS", "ASRNL.AS", "KPN.AS", "NN.AS", "PHIA.AS",
    "RAND.AS", "SBMO.AS", "TKWY.AS", "UMG.AS", "WKL.AS"
]

def check_tickers():
    print(f"Checking {len(aex_tickers)} AEX tickers...")
    results = []
    for ticker_sym in aex_tickers[:5]: # Check first 5 for testing
        print(f"Fetching {ticker_sym}...")
        tk = yf.Ticker(ticker_sym)
        try:
            price = tk.fast_info.get('lastPrice')
            fcf = tk.cashflow.loc['Free Cash Flow'].iloc[0] if 'Free Cash Flow' in tk.cashflow.index else "N/A"
            results.append({"ticker": ticker_sym, "price": price, "fcf": fcf})
        except Exception as e:
            results.append({"ticker": ticker_sym, "error": str(e)})
            
    for res in results:
        print(res)

if __name__ == "__main__":
    check_tickers()
