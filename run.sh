#!/bin/bash

echo "========================================="
echo "  Stock Trading Algo - Interactive Run   "
echo "========================================="
echo "Select an action:"
echo "1) Backtest"
echo "2) Scan Market"
echo "3) Valuation"
echo "4) Exit"
read -p "Option (1-4): " option

case $option in
  1)
    read -p "Enter Ticker (e.g. AAPL): " ticker
    read -p "Enter Period (e.g. 2y, 6mo) [default: from config]: " period
    cmd="python3 main.py backtest"
    if [ -n "$ticker" ]; then cmd="$cmd --ticker \"$ticker\""; fi
    if [ -n "$period" ]; then cmd="$cmd --period \"$period\""; fi
    echo "Running: $cmd"
    eval "$cmd"
    ;;
  2)
    echo "Select Engine:"
    echo "1) Classic"
    echo "2) Growth"
    echo "3) Revenue"
    echo "4) EBITDA"
    read -p "Option (1-4) [default: from config]: " engine_opt
    engine=""
    case $engine_opt in
      1) engine="classic" ;;
      2) engine="growth" ;;
      3) engine="revenue" ;;
      4) engine="ebitda" ;;
    esac
    
    read -p "Enter Index (e.g. SP500, AEX, DAX, NASDAQ, FTSE) [default: AEX]: " index
    cmd="python3 main.py scan"
    if [ -n "$index" ]; then cmd="$cmd --index \"$index\""; fi
    if [ -n "$engine" ]; then cmd="$cmd --engine \"$engine\""; fi
    echo "Running: $cmd"
    eval "$cmd"
    ;;
  3)
    read -p "Enter Ticker (e.g. MSFT): " ticker
    if [ -z "$ticker" ]; then
      echo "Ticker is required for valuation."
      exit 1
    fi
    echo "Select Engine:"
    echo "1) Classic"
    echo "2) Growth"
    echo "3) Revenue"
    echo "4) EBITDA"
    read -p "Option (1-4) [default: classic]: " engine_opt
    engine=""
    case $engine_opt in
      1) engine="classic" ;;
      2) engine="growth" ;;
      3) engine="revenue" ;;
      4) engine="ebitda" ;;
    esac
    read -p "Run Monte Carlo Sensitivity Analysis? (y/n) [default: n]: " sens
    cmd="python3 main.py valuation --ticker \"$ticker\""
    if [ -n "$engine" ]; then cmd="$cmd --engine \"$engine\""; fi
    if [[ "$sens" == "y" || "$sens" == "Y" ]]; then cmd="$cmd --sensitivity"; fi
    echo "Running: $cmd"
    eval "$cmd"
    ;;
  4)
    echo "Exiting..."
    exit 0
    ;;
  *)
    echo "Invalid option."
    exit 1
    ;;
esac
