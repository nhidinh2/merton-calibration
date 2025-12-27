"""
Asset Value and Volatility Calibration

Calibrate unobservable asset value (V) and asset volatility (sigma_V)
from observable equity value (E) and equity volatility (sigma_E).
"""

import numpy as np
from scipy.optimize import fsolve
from scipy.stats import norm

from improved.model import black_scholes_call, black_scholes_vega, black_scholes_delta


def calibrate_asset_parameters(E, sigma_E_smooth, D, T, r, V0=None, sigma_V0=None):
    """
    Calibrate asset value (V) and asset volatility (sigma_V) from equity data.
    
    This solves the system of equations:
    1. E = BlackScholes(V, D, T, r, sigma_V)
    2. sigma_E * E = vega(V, D, T, r, sigma_V) * sigma_V * V
    
    Parameters:
    -----------
    E : float
        Market value of equity
    sigma_E_smooth : float
        Equity volatility (annualized)
    D : float
        Face value of debt
    T : float
        Time to maturity (in years)
    r : float
        Risk-free rate (annualized)
    V0 : float, optional
        Initial guess for asset value (default: E + D)
    sigma_V0 : float, optional
        Initial guess for asset volatility (default: sigma_E_smooth * E / (E + D))
    
    Returns:
    --------
    tuple (V, sigma_V)
        Estimated asset value and asset volatility
    """
    
    if V0 is None:
        V0 = E + D # Simple initial guess
    if sigma_V0 is None:
        sigma_V0 = sigma_E_smooth * E / (E + D) if (E + D) > 0 else sigma_E_smooth
    
    V0 = max(float(V0), 1e-6)
    sigma_V0 = max(float(sigma_V0), 1e-6)

    def equations(params):
        """
        System of equations to solve.
        
        Returns:
        --------
        list [eq1, eq2]
            Residuals that should be zero at solution
        """
        V, sigma_V = params
        
        E_calc = black_scholes_call(V, D, T, r, sigma_V)
        eq1 = E_calc - E
    
        delta = black_scholes_delta(V, D, T, r, sigma_V)
        E_vol_calc = (delta * sigma_V * V) / E if E > 0 else 0
        eq2 = E_vol_calc - sigma_E_smooth
        
        return [eq1, eq2]

    try:
        V, sigma_V = fsolve(equations, [V0, sigma_V0], xtol=1e-6, maxfev=5000)
        V = max(V, 1e-6)
        sigma_V = max(sigma_V, 1e-6)
        return V, sigma_V

    except Exception as e:
        # On failure, use standard approximation
        V = E + D
        sigma_V = sigma_E_smooth * E / (E + D) if (E + D) > 0 else sigma_E_smooth
        V = max(V, 1e-6)
        sigma_V = max(sigma_V, 1e-6)
        return V, sigma_V


