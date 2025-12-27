"""
Fetch Real Firm Data from Financial APIs

This script downloads real market data from:
- Yahoo Finance (yfinance): Equity prices and volatility
- FRED (Federal Reserve Economic Data): Risk-free rates (10Y Treasury)
- Yahoo Finance Balance Sheet: Debt data (quarterly)

Firms included:
- AAPL: Apple Inc. (Technology)
- JPM: JPMorgan Chase (Financial)
- TSLA: Tesla Inc. (Automotive/Technology)
- XOM: Exxon Mobil (Energy)
- F: Ford Motor Company (Automotive)
"""

import pandas as pd
import numpy as np
import yfinance as yf
import os
import warnings
warnings.filterwarnings('ignore')

# Try to import fredapi, but make it optional
try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False
    print("Warning: fredapi not available. Risk-free rates will use approximate values.")
    print("To install: pip install fredapi")
    print("Note: FRED API key required (free from https://fred.stlouisfed.org/docs/api/api_key.html)")


def fetch_equity_data(ticker, start_date, end_date):
    """
    Fetch equity price and volatility data from Yahoo Finance.
    
    Parameters:
    -----------
    ticker : str
        Stock ticker symbol
    start_date : str
        Start date (YYYY-MM-DD)
    end_date : str
        End date (YYYY-MM-DD)
    
    Returns:
    --------
    tuple (prices_df, vols_df)
        DataFrames with date, firm_id, equity_price and date, firm_id, equity_vol
    """
    print(f"  Fetching equity data for {ticker}...")
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            print(f"    Warning: No data found for {ticker}")
            return None, None
        
        # Calculate realized volatility (rolling 30-day)
        hist['returns'] = hist['Close'].pct_change()
        hist['vol_30d'] = hist['returns'].rolling(window=30).std() * np.sqrt(252)  # Annualized
        
        # Fill NaN values with overall volatility
        overall_vol = hist['returns'].std() * np.sqrt(252)
        hist['vol_30d'] = hist['vol_30d'].fillna(overall_vol)
        
        # Prepare equity prices and volatilities in one pass
        data = []
        for date, row in hist.iterrows():
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'firm_id': ticker,
                'equity_price': round(row['Close'], 2),
                'equity_vol': round(row['vol_30d'], 4)
            })
        
        df = pd.DataFrame(data)
        prices_df = df[['date', 'firm_id', 'equity_price']].copy()
        vols_df = df[['date', 'firm_id', 'equity_vol']].copy()
        
        return prices_df, vols_df
        
    except Exception as e:
        print(f"    Error fetching data for {ticker}: {e}")
        return None, None


def fetch_debt_data(ticker, start_date, end_date):
    """
    Fetch quarterly debt data from Yahoo Finance balance sheet.
    
    Parameters:
    -----------
    ticker : str
        Stock ticker symbol
    start_date : str
        Start date (YYYY-MM-DD)
    end_date : str
        End date (YYYY-MM-DD)
    
    Returns:
    --------
    DataFrame with date, firm_id, debt
    """
    print(f"  Fetching debt data for {ticker}...")
    
    try:
        stock = yf.Ticker(ticker)
        balance_sheet = stock.balance_sheet
        
        if balance_sheet.empty:
            print(f"    Warning: No balance sheet data for {ticker}")
            return None
        
        # Look for total debt (try different column names)
        debt_cols = ['Total Debt', 'Total Liabilities', 'Long Term Debt', 'Debt']
        debt_col = None
        
        for col in debt_cols:
            if col in balance_sheet.index:
                debt_col = col
                break
        
        if debt_col is None:
            # Try to find any debt-related column
            debt_col = balance_sheet.index[balance_sheet.index.str.contains('Debt', case=False, na=False)]
            if len(debt_col) > 0:
                debt_col = debt_col[0]
            else:
                print(f"    Warning: Could not find debt column for {ticker}")
                return None
        
        # Get debt values (in millions)
        debt_series = balance_sheet.loc[debt_col]
        
        # Filter by date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        debt_data = []
        for date, value in debt_series.items():
            if start_dt <= date <= end_dt:
                # Skip NaN values
                if pd.isna(value):
                    continue
                try:
                    debt_value = round(float(value) / 1e6, 2)  # Convert to millions
                    debt_data.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'firm_id': ticker,
                        'debt': debt_value
                    })
                except (ValueError, TypeError):
                    pass
        
        if not debt_data:
            # If no data in range, find the nearest valid (non-NaN) value
            # Try most recent value <= end_dt, then earliest value > end_dt
            for date in reversed(debt_series.index[debt_series.index <= end_dt]):
                value = debt_series[date]
                if not pd.isna(value):
                    try:
                        debt_data.append({
                            'date': end_date,
                            'firm_id': ticker,
                            'debt': round(float(value) / 1e6, 2)
                        })
                        break
                    except (ValueError, TypeError):
                        continue
            
            # If still no data, try future dates
            if not debt_data:
                for date in sorted(debt_series.index[debt_series.index > end_dt]):
                    value = debt_series[date]
                    if not pd.isna(value):
                        try:
                            debt_data.append({
                                'date': end_date,
                                'firm_id': ticker,
                                'debt': round(float(value) / 1e6, 2)
                            })
                            break
                        except (ValueError, TypeError):
                            continue
        
        if not debt_data:
            return None
        
        return pd.DataFrame(debt_data)
        
    except Exception as e:
        print(f"    Error fetching debt data for {ticker}: {e}")
        return None


def fetch_risk_free_rate(start_date, end_date, fred_api_key=None):
    """
    Fetch risk-free rate (10Y Treasury) from FRED API.
    
    Parameters:
    -----------
    start_date : str
        Start date (YYYY-MM-DD)
    end_date : str
        End date (YYYY-MM-DD)
    fred_api_key : str, optional
        FRED API key (if not provided, will use approximate values)
    
    Returns:
    --------
    DataFrame with date, risk_free_rate
    """
    print("  Fetching risk-free rate data...")
    
    if not FRED_AVAILABLE or fred_api_key is None:
        print("    Using approximate risk-free rates (install fredapi and provide API key for real data)")
        # Approximate 10Y Treasury rates for 2020 (low rates during COVID)
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        # Approximate: started around 1.8%, dropped to ~0.6% during COVID, recovered to ~0.9%
        base_rates = np.linspace(0.018, 0.009, len(dates))
        risk_free_data = [{
            'date': date.strftime('%Y-%m-%d'),
            'risk_free_rate': round(rate, 4)
        } for date, rate in zip(dates, base_rates)]
        return pd.DataFrame(risk_free_data)
    
    try:
        fred = Fred(api_key=fred_api_key)
        # 10-Year Treasury Constant Maturity Rate
        series = fred.get_series('DGS10', start=start_date, end=end_date)
        
        if series.empty:
            print("    Warning: No FRED data available, using approximate values")
            # Fall back to approximate rates
            dates = pd.date_range(start=start_date, end=end_date, freq='B')
            base_rates = np.linspace(0.018, 0.009, len(dates))
            return pd.DataFrame([{
                'date': date.strftime('%Y-%m-%d'),
                'risk_free_rate': round(rate, 4)
            } for date, rate in zip(dates, base_rates)])
        
        # Convert to daily (forward fill)
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        series_daily = series.reindex(dates, method='ffill')
        
        risk_free_data = [{
            'date': date.strftime('%Y-%m-%d'),
            'risk_free_rate': round(rate / 100.0, 4)  # Convert from percentage to decimal
        } for date, rate in series_daily.items() if not pd.isna(rate)]
        
        return pd.DataFrame(risk_free_data)
        
    except Exception as e:
        print(f"    Error fetching FRED data: {e}")
        print("    Using approximate risk-free rates")
        # Fall back to approximate rates
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        base_rates = np.linspace(0.018, 0.009, len(dates))
        return pd.DataFrame([{
            'date': date.strftime('%Y-%m-%d'),
            'risk_free_rate': round(rate, 4)
        } for date, rate in zip(dates, base_rates)])


def generate_real_firm_data(start_date='2020-01-01', end_date='2020-12-31', fred_api_key=None):
    """
    Fetch real firm data from financial APIs.
    
    Parameters:
    -----------
    start_date : str
        Start date (YYYY-MM-DD)
    end_date : str
        End date (YYYY-MM-DD)
    fred_api_key : str, optional
        FRED API key for risk-free rate data
    """
    print("Fetching real firm data from financial APIs...")
    print("=" * 60)
    
    # Firm tickers
    tickers = ['AAPL', 'JPM', 'TSLA', 'XOM', 'F']

    all_equity_prices = []
    all_equity_vols = []
    all_debt_data = []

    # Fetch data for each firm
    for ticker in tickers:
        prices_df, vols_df = fetch_equity_data(ticker, start_date, end_date)
        if prices_df is not None:
            all_equity_prices.append(prices_df)
        if vols_df is not None:
            all_equity_vols.append(vols_df)

        debt_df = fetch_debt_data(ticker, start_date, end_date)
        if debt_df is not None:
            all_debt_data.append(debt_df)

    # Combine all firm data
    equity_prices_df = pd.concat(all_equity_prices, ignore_index=True) if all_equity_prices else pd.DataFrame()
    equity_vols_df = pd.concat(all_equity_vols, ignore_index=True) if all_equity_vols else pd.DataFrame()
    debt_df = pd.concat(all_debt_data, ignore_index=True) if all_debt_data else pd.DataFrame()
    
    # Fetch risk-free rate
    risk_free_df = fetch_risk_free_rate(start_date, end_date, fred_api_key)
    
    # Save to CSV
    from pathlib import Path
    output_dir = Path(__file__).parent.parent / 'real'
    output_dir.mkdir(exist_ok=True)
    
    equity_prices_df.to_csv(output_dir / 'equity_prices.csv', index=False)
    equity_vols_df.to_csv(output_dir / 'equity_vol.csv', index=False)
    debt_df.to_csv(output_dir / 'debt_quarterly.csv', index=False)
    risk_free_df.to_csv(output_dir / 'risk_free.csv', index=False)
    
    print("\n" + "=" * 60)
    print(f"Generated real firm data files in {output_dir}/")
    print(f"  - equity_prices.csv: {len(equity_prices_df)} rows")
    print(f"  - equity_vol.csv: {len(equity_vols_df)} rows")
    print(f"  - debt_quarterly.csv: {len(debt_df)} rows")
    print(f"  - risk_free.csv: {len(risk_free_df)} rows")
    print("\nFirms included:")
    for ticker in tickers:
        print(f"  {ticker}")


if __name__ == "__main__":
    import sys
    
    # Check for FRED API key in environment variable or command line
    fred_key = os.environ.get('FRED_API_KEY')
    if len(sys.argv) > 1:
        fred_key = sys.argv[1]
    
    if not fred_key and FRED_AVAILABLE:
        print("Note: FRED API key not provided.")
        print("Set FRED_API_KEY environment variable or pass as argument for real risk-free rates.")
        print("Get free API key from: https://fred.stlouisfed.org/docs/api/api_key.html")
        print()
    
    generate_real_firm_data(fred_api_key=fred_key)