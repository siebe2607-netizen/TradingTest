import yfinance as yf

def get_fundamentals(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    
    # Financials
    cash_flow = ticker.cashflow
    balance_sheet = ticker.balance_sheet
    financials = ticker.financials
    
    print(f"--- Fundamentals for {ticker_symbol} ---")
    
    try:
        # Free Cash Flow
        fcf = ticker.cashflow.loc['Free Cash Flow'].iloc[0]
        print(f"Free Cash Flow: {fcf}")
    except Exception as e:
        print(f"FCF not found directly. Error: {e}")

    try:
        # Shares Outstanding
        shares = ticker.info.get('sharesOutstanding')
        print(f"Shares Outstanding: {shares}")
    except Exception as e:
        print(f"Shares info not found. Error: {e}")

    try:
        # Growth estimates (sometimes available)
        growth = ticker.info.get('earningsGrowth')
        print(f"Earnings Growth Estimate: {growth}")
    except Exception as e:
        print(f"Growth info not found. Error: {e}")

if __name__ == "__main__":
    get_fundamentals("ADYEN.AS")
