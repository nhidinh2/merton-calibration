"""
Reference Merton model implementation for validation.

This module provides a reference implementation that wraps
the naive_model functions for use in validation scripts.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from naive_model.model import black_scholes_call
from naive_model.calibration import calibrate_asset_parameters
from naive_model.risk_measures import compute_risk_measures


def merton_model(E, sigma_E, D, T, r):
    """
    Reference Merton model implementation.
    
    This function provides a simple interface for validation purposes.
    It calibrates asset parameters and computes risk measures.
    
    Parameters:
    -----------
    E : float
        Market value of equity
    sigma_E : float
        Equity volatility (annualized)
    D : float
        Face value of debt
    T : float
        Time to maturity (in years)
    r : float
        Risk-free rate (annualized)
    
    Returns:
    --------
    dict
        Dictionary with keys: 'V', 'sigma_V', 'DD', 'PD'
    """
    # Calibrate asset parameters
    V, sigma_V = calibrate_asset_parameters(E, sigma_E, D, T, r)
    
    # Compute risk measures
    risk = compute_risk_measures(V, D, T, r, sigma_V)
    
    return {
        'V': V,
        'sigma_V': sigma_V,
        'DD': risk['DD'],
        'PD': risk['PD']
    }

