"""
Entry point for baseline Merton model.

Run with: python -m improved
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from improved.calibration import calibrate_asset_parameters
from improved.risk_measures import compute_risk_measures
from improved.smoothing import smooth_equity_volatility, plot_smoothed_volatility


def main():
    """
    Main entry point for baseline model.
    
    This function:
    1. Loads data (equity prices, equity vol, debt, risk-free rates)
    2. Smooths equity volatility using EWMA
    3. Aligns debt to daily (forward-fill quarterly values)
    4. For each firm and date, calibrates asset value and volatility
    5. Computes risk measures (DD, PD)
    6. Saves results to CSV
    """
    # Load all data
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / 'data' / 'real'
    equity_prices = pd.read_csv(data_dir / 'equity_prices.csv', parse_dates=['date'])
    equity_vol = pd.read_csv(data_dir / 'equity_vol.csv', parse_dates=['date'])
    debt = pd.read_csv(data_dir / 'debt_quarterly.csv', parse_dates=['date'])
    risk_free = pd.read_csv(data_dir / 'risk_free.csv', parse_dates=['date'])

    # Smooth equity volatility
    equity_vol_smooth = smooth_equity_volatility(equity_vol.copy())
    
    # Plot smoothed volatility
    output_dir = project_root / 'outputs'
    output_dir.mkdir(exist_ok=True)
    plot_smoothed_volatility(equity_vol_smooth, output_path=output_dir / 'smoothed_volatility.png')

    # Align debt to daily (forward-fill quarterly values)
    debt_daily_list = []
    for firm_id in debt['firm_id'].unique():
        firm_debt = debt[debt['firm_id'] == firm_id].set_index('date')
        firm_equity_dates = equity_prices[equity_prices['firm_id'] == firm_id]['date'].unique()
        
        if len(firm_debt) == 0 or len(firm_equity_dates) == 0:
            continue
        
        # Reindex to daily, using backward-fill then forward-fill to handle quarterly debt data
        all_dates = sorted(set(list(firm_equity_dates) + list(firm_debt.index)))
        firm_debt_daily = firm_debt.reindex(all_dates).bfill().ffill().reset_index()
        # Filter to only equity dates
        firm_debt_daily = firm_debt_daily[firm_debt_daily['date'].isin(firm_equity_dates)]
        firm_debt_daily['firm_id'] = firm_id
        firm_debt_daily = firm_debt_daily[['date', 'firm_id', 'debt']]
        debt_daily_list.append(firm_debt_daily)
    
    if debt_daily_list:
        debt_daily = pd.concat(debt_daily_list, ignore_index=True)
    else:
        debt_daily = pd.DataFrame(columns=['date', 'firm_id', 'debt'])

    # Shares outstanding (in billions) as of Dec 31, 2020
    # Source: Approximate shares outstanding from financial data
    shares_outstanding = {
        'AAPL': 16.93,  # ~16.93 billion shares
        'JPM': 3.09,    # ~3.09 billion shares
        'TSLA': 3.325,  # ~3.325 billion shares (est.)
        'XOM': 4.25,    # ~4.2-4.3 billion shares
        'F': 3.97       # ~3.97 billion shares
    }

    # For each firm and date, calibrate and compute
    results = []
    T = 1.0  # Time to maturity (1 year)

    for firm_id in equity_prices['firm_id'].unique():
        firm_equity = equity_prices[equity_prices['firm_id'] == firm_id].sort_values('date')
        firm_vol = equity_vol_smooth[equity_vol_smooth['firm_id'] == firm_id].sort_values('date')
        firm_debt = debt_daily[debt_daily['firm_id'] == firm_id].sort_values('date')
        firm_rf = risk_free.sort_values('date')
        
        # Track previous period's solution for warm start
        V_prev = None
        sigma_V_prev = None
        
        for date in firm_equity['date']:
            # Get values for this date
            equity_row = firm_equity[firm_equity['date'] == date]
            vol_row = firm_vol[firm_vol['date'] == date]
            debt_row = firm_debt[firm_debt['date'] == date]
            rf_row = firm_rf[firm_rf['date'] == date]
            
            # Skip if any data is missing
            if len(equity_row) == 0 or len(vol_row) == 0 or len(debt_row) == 0 or len(rf_row) == 0:
                continue
            
            E_per_share = equity_row['equity_price'].values[0]
            sigma_E_smooth = vol_row['equity_vol'].values[0]
            D = debt_row['debt'].values[0]
            r = rf_row['risk_free_rate'].values[0]
            
            # Skip if any value is invalid
            if pd.isna(E_per_share) or pd.isna(sigma_E_smooth) or pd.isna(D) or pd.isna(r):
                continue
            if E_per_share <= 0 or sigma_E_smooth <= 0 or D <= 0 or r < 0:
                continue
            
            # Get shares outstanding for this firm
            if firm_id not in shares_outstanding:
                print(f"Warning: No shares outstanding data for {firm_id}, skipping")
                continue
            
            shares_billions = shares_outstanding[firm_id]
            
            # Convert equity from per-share to total market cap (in millions)
            # E_per_share is in dollars, shares is in billions
            # E_total = (E_per_share * shares_billions * 1e9) / 1e6 = E_per_share * shares_billions * 1000
            E = E_per_share * shares_billions * 1000.0
            
            # Set initial guess: use previous period's solution if available, otherwise use standard approximation
            if V_prev is not None and sigma_V_prev is not None:
                V0 = V_prev
                sigma_V0 = sigma_V_prev
            else:
                # Standard approximation for initial observation
                V0 = E + D
                sigma_V0 = sigma_E_smooth * E / (E + D) if (E + D) > 0 else sigma_E_smooth
            
            try:
                # Calibrate using total values (E and D both in millions)
                V, sigma_V = calibrate_asset_parameters(E, sigma_E_smooth, D, T, r, V0=V0, sigma_V0=sigma_V0)
                
                # Update previous solution for next iteration
                V_prev = V
                sigma_V_prev = sigma_V
                
                # Compute risk measures using total values
                risk = compute_risk_measures(V, D, T, r, sigma_V)
                
                results.append({
                    'date': date,
                    'firm_id': firm_id,
                    'V': V,  # Total asset value in millions
                    'sigma_V': sigma_V,
                    'DD': risk['DD'],
                    'PD': risk['PD']
                })
            except Exception as e:
                # On convergence failure, reset to standard approximation for next iteration
                V_prev = None
                sigma_V_prev = None
                print(f"Error processing {firm_id} on {date}: {e}")
                continue
    
    # Save results
    results_df = pd.DataFrame(results)
    
    if len(results_df) == 0:
        print("No results generated. Check data quality.")
        return
    
    output_file = output_dir / 'improved_results.csv'
    results_df.to_csv(output_file, index=False)
    
    print(f"Results saved to {output_file}")
    print(f"Total observations: {len(results_df)}")


if __name__ == "__main__":
    main()
