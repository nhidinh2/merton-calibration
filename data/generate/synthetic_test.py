"""
Synthetic Data Generator for Merton Model Testing

This script generates synthetic firm data with known parameters.
The generated data can be used to validate calibration accuracy.

Run this script to generate CSV files in data/synthetic/
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from scipy.stats import norm
import os
import sys
from pathlib import Path

# Add parent directory to path to import merton_reference
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from model.baseline.merton_reference import merton_model
from model.naive_model.model import black_scholes_call


def generate_synthetic_firm_data(firm_id, V0, sigma_V, D, T, r, n_days=252, start_date='2020-01-01'):
    """
    Generate synthetic equity prices and volatilities for a firm.
    
    Parameters:
    -----------
    firm_id : str
        Firm identifier
    V0 : float
        Initial asset value (ground truth)
    sigma_V : float
        Asset volatility (ground truth)
    D : float
        Debt face value
    T : float
        Time to maturity (years)
    r : float
        Risk-free rate
    n_days : int
        Number of trading days to generate
    start_date : str
        Start date for the time series
    
    Returns:
    --------
    tuple (dates, equity_prices, equity_vols, debt_values)
    """
    dates = pd.date_range(start=start_date, periods=n_days, freq='B')  # Business days
    
    # Generate asset value path using geometric Brownian motion
    dt = 1/252  # Daily time step
    n_steps = len(dates)
    
    # Random shocks
    np.random.seed(hash(firm_id) % 2**32)  # Deterministic seed based on firm_id
    shocks = np.random.randn(n_steps)
    
    # Asset value path: dV = r*V*dt + sigma_V*V*dW
    V_path = np.zeros(n_steps)
    V_path[0] = V0
    
    for i in range(1, n_steps):
        V_path[i] = V_path[i-1] * np.exp((r - 0.5 * sigma_V**2) * dt + sigma_V * np.sqrt(dt) * shocks[i])
    
    # Calculate equity value at each point using Black-Scholes
    equity_prices = []
    equity_vols = []
    
    for i, V_t in enumerate(V_path):
        # Time remaining to maturity
        T_remaining = max(T - i * dt, 0.01)  # Ensure positive time
        
        # Equity value = call option on assets
        E_t = black_scholes_call(V_t, D, T_remaining, r, sigma_V)
        equity_prices.append(max(E_t, 0.01))  # Ensure positive
        
        # Approximate equity volatility (simplified)
        # In practice, this would come from historical returns or implied vol
        # Here we use a simple approximation: sigma_E ≈ sigma_V * (V/E) * (dE/dV)
        if E_t > 0:
            # Delta of the call option
            d1 = (np.log(V_t / D) + (r + 0.5 * sigma_V**2) * T_remaining) / (sigma_V * np.sqrt(T_remaining))
            delta = norm.cdf(d1) if T_remaining > 0 else 1.0
            sigma_E_approx = sigma_V * (V_t / E_t) * delta
        else:
            sigma_E_approx = sigma_V
        
        # Add some noise to make it realistic
        sigma_E_approx *= (1 + 0.1 * np.random.randn())
        equity_vols.append(max(sigma_E_approx, 0.05))  # Minimum 5% volatility
    
    # Debt values (quarterly, constant for simplicity)
    quarterly_dates = pd.date_range(start=start_date, end=dates[-1], freq='QE')
    debt_values = [D] * len(quarterly_dates)
    
    return dates, equity_prices, equity_vols, quarterly_dates, debt_values


def calculate_firm_parameters(leverage_ratio, sigma_V, target_DD, r, T, base_V=100.0):
    """
    Calculate firm parameters (V0, D) from financial ratios and risk targets.
    
    Mathematical foundation:
    - Leverage ratio: L = D/V (debt-to-asset ratio)
    - Asset value follows: dV = r*V*dt + σ_V*V*dW (geometric Brownian motion)
    - At maturity T: V_T ~ lognormal with E[V_T] = V_0*exp(r*T)
    - Distance-to-default: DD = (E[V_T] - D) / std(V_T)
    
    Given leverage ratio L and asset volatility σ_V, we derive:
    - D = L * V_0
    - V_0 is scaled by base_V to set firm size
    
    Parameters:
    -----------
    leverage_ratio : float
        Debt-to-asset ratio (D/V), typically in [0, 1]
    sigma_V : float
        Asset volatility (annualized), typically in [0.1, 0.5]
    target_DD : float
        Target distance-to-default (used for validation, not strictly enforced)
    r : float
        Risk-free rate (annualized)
    T : float
        Time to maturity (years)
    base_V : float
        Base asset value (scales the firm size)
    
    Returns:
    --------
    dict with 'V0', 'D', 'sigma_V', 'T', 'leverage_ratio', 'expected_DD'
    """
    # From leverage ratio: D = leverage_ratio * V
    # From distance-to-default formula:
    #   DD = (V_T_expected - D) / V_T_std
    #   where V_T_expected = V * exp(r*T)
    #   and V_T_std = V * exp(r*T) * sqrt(exp(sigma_V^2*T) - 1)
    
    # We want: target_DD = (V*exp(r*T) - D) / (V*exp(r*T)*sqrt(exp(sigma_V^2*T)-1))
    # With D = leverage_ratio * V:
    #   target_DD = (V*exp(r*T) - leverage_ratio*V) / (V*exp(r*T)*sqrt(exp(sigma_V^2*T)-1))
    #   target_DD = (exp(r*T) - leverage_ratio) / (exp(r*T)*sqrt(exp(sigma_V^2*T)-1))
    
    # Solve for V0 that gives us the target DD
    exp_rT = np.exp(r * T)
    sqrt_term = np.sqrt(np.exp(sigma_V**2 * T) - 1)
    
    # Rearranging: V0 = base_V * scale_factor
    # We'll use base_V as the scale and adjust to hit target_DD
    V0 = base_V
    D = leverage_ratio * V0
    
    # Calculate actual DD
    V_T_expected = V0 * exp_rT
    V_T_std = V0 * exp_rT * sqrt_term
    actual_DD = (V_T_expected - D) / V_T_std if V_T_std > 0 else 0
    
    # If actual_DD doesn't match target, we can scale V0
    # But for simplicity, we'll use the leverage ratio directly
    # and accept that DD will vary based on the combination
    
    return {
        'V0': V0,
        'D': D,
        'sigma_V': sigma_V,
        'T': T,
        'leverage_ratio': leverage_ratio,
        'expected_DD': actual_DD
    }


def generate_all_synthetic_data():
    """
    Generate synthetic data for multiple firms with different characteristics.
    
    Firms are defined by:
    - Leverage ratio (D/V): debt-to-asset ratio
    - Asset volatility (σ_V): fundamental risk parameter
    - These determine the firm's risk profile mathematically
    """
    r = 0.05  # 5% risk-free rate (constant)
    T = 1.0   # 1 year to maturity
    
    # Define firms by financial ratios and risk characteristics
    # Each firm is specified by (leverage_ratio, sigma_V, base_V, description)
    firm_specs = [
        # Low risk: low leverage, low volatility
        ('FIRM_A', 0.30, 0.15, 200.0, 'Low risk: low leverage (30%), low volatility (15%)'),
        
        # Medium risk: moderate leverage, moderate volatility
        ('FIRM_B', 0.50, 0.25, 150.0, 'Medium risk: moderate leverage (50%), moderate volatility (25%)'),
        
        # High risk: high leverage, high volatility
        ('FIRM_C', 0.60, 0.40, 100.0, 'High risk: high leverage (60%), high volatility (40%)'),
        
        # Very low risk: very low leverage, low volatility
        ('FIRM_D', 0.20, 0.20, 300.0, 'Very low risk: very low leverage (20%), low volatility (20%)'),
        
        # Distressed: very high leverage, high volatility
        ('FIRM_E', 0.85, 0.35, 80.0, 'Distressed: very high leverage (85%), high volatility (35%)'),
    ]
    
    firms = []
    for firm_id, leverage, sigma_V, base_V, description in firm_specs:
        params = calculate_firm_parameters(leverage, sigma_V, target_DD=2.0, r=r, T=T, base_V=base_V)
        params['id'] = firm_id
        params['description'] = description
        firms.append(params)
        
    n_days = 252  # 1 year of trading days
    start_date = '2020-01-01'
    
    # Collect all data
    all_equity_prices = []
    all_equity_vols = []
    all_debt_data = []
    
    for firm in firms:
        dates, equity_prices, equity_vols, debt_dates, debt_values = generate_synthetic_firm_data(
            firm['id'], firm['V0'], firm['sigma_V'], firm['D'], firm['T'], r, n_days, start_date
        )
        
        # Equity prices
        for date, price in zip(dates, equity_prices):
            all_equity_prices.append({
                'date': date.strftime('%Y-%m-%d'),
                'firm_id': firm['id'],
                'equity_price': round(price, 2)
            })
        
        # Equity volatilities
        for date, vol in zip(dates, equity_vols):
            all_equity_vols.append({
                'date': date.strftime('%Y-%m-%d'),
                'firm_id': firm['id'],
                'equity_vol': round(vol, 4)
            })
        
        # Debt (quarterly)
        for date, debt in zip(debt_dates, debt_values):
            all_debt_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'firm_id': firm['id'],
                'debt': round(debt, 2)
            })
    
    # Create DataFrames
    equity_prices_df = pd.DataFrame(all_equity_prices)
    equity_vols_df = pd.DataFrame(all_equity_vols)
    debt_df = pd.DataFrame(all_debt_data)
    
    # Risk-free rate (constant)
    risk_free_df = pd.DataFrame({
        'date': pd.date_range(start=start_date, periods=n_days, freq='B').strftime('%Y-%m-%d'),
        'risk_free_rate': [r] * n_days
    })
    
    # Save to CSV
    output_dir = Path(__file__).parent.parent / 'synthetic'
    output_dir.mkdir(exist_ok=True)
    
    equity_prices_df.to_csv(output_dir / 'equity_prices.csv', index=False)
    equity_vols_df.to_csv(output_dir / 'equity_vol.csv', index=False)
    debt_df.to_csv(output_dir / 'debt_quarterly.csv', index=False)
    risk_free_df.to_csv(output_dir / 'risk_free.csv', index=False)
    
    print(f"Generated synthetic data files in {output_dir}/")
    print(f"  - equity_prices.csv: {len(equity_prices_df)} rows")
    print(f"  - equity_vol.csv: {len(equity_vols_df)} rows")
    print(f"  - debt_quarterly.csv: {len(debt_df)} rows")
    print(f"  - risk_free.csv: {len(risk_free_df)} rows")
    print("\nFirm parameters (ground truth for validation):")
    print("  Format: Firm | Leverage (D/V) | Asset Vol (σ_V) | V0 | D | E0")
    print("  " + "-" * 70)
    for firm in firms:
        V0, D = firm['V0'], firm['D']
        E0 = V0 - D
        leverage = firm['leverage_ratio']
        sigma_V = firm['sigma_V']
        print(f"  {firm['id']:8s} | {leverage:6.1%} | {sigma_V:13.1%} | {V0:5.1f} | {D:5.1f} | {E0:5.1f}")


if __name__ == "__main__":
    print("Generating synthetic firm data...")
    generate_all_synthetic_data()
    print("\nDone! You can now use these files to test the Merton model calibration.")

