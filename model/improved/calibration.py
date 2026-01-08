"""
Asset Value and Volatility Calibration

Calibrate unobservable asset value (V) and asset volatility (sigma_V)
from observable equity value (E) and equity volatility (sigma_E).
"""

import numpy as np
from scipy.optimize import fsolve, least_squares
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


def calibrate_asset_parameters_bounded(
    E, 
    sigma_E_smooth, 
    D, 
    T, 
    r, 
    V0=None, 
    sigma_V0=None,
    sigma_V_min=0.05,
    sigma_V_max=0.80,
    leverage_min=0.10,
    leverage_max=0.95,
    lambda_sigma=0.1,
    lambda_V=0.1,
    sigma_V_prior=None,
    V_prior=None
):
    """
    Calibrate asset value (V) and asset volatility (sigma_V) using constrained 
    nonlinear least squares with bounds and regularization.
    
    This solves the constrained optimization problem:
    
    min_{V, sigma_V} ||[E - BS(V, D, T, r, sigma_V), 
                        sigma_E - (delta * sigma_V * V) / E]||^2
                      + lambda_sigma * (sigma_V - sigma_V_prior)^2
                      + lambda_V * (V/V_prior - 1)^2
    
    subject to:
    - sigma_V_min <= sigma_V <= sigma_V_max
    - leverage_min <= D/V <= leverage_max (i.e., D/leverage_max <= V <= D/leverage_min)
    - V > 0
    
    Parameters:
    -----------
    E : float
        Market value of equity
    sigma_E_smooth : float
        Equity volatility (annualized, smoothed)
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
    sigma_V_min : float, optional
        Minimum asset volatility bound (default: 0.05)
    sigma_V_max : float, optional
        Maximum asset volatility bound (default: 0.80)
    leverage_min : float, optional
        Minimum leverage (D/V) bound (default: 0.10)
    leverage_max : float, optional
        Maximum leverage (D/V) bound (default: 0.95)
    lambda_sigma : float, optional
        Regularization weight for sigma_V (default: 0.1)
    lambda_V : float, optional
        Regularization weight for V (default: 0.1)
    sigma_V_prior : float, optional
        Prior value for sigma_V in regularization (default: sigma_V0)
    V_prior : float, optional
        Prior value for V in regularization (default: V0)
    
    Returns:
    --------
    tuple (V, sigma_V)
        Estimated asset value and asset volatility
    """
    
    # Set initial guesses
    if V0 is None:
        V0 = E + D
    if sigma_V0 is None:
        sigma_V0 = sigma_E_smooth * E / (E + D) if (E + D) > 0 else sigma_E_smooth
    
    V0 = max(float(V0), 1e-6)
    sigma_V0 = max(float(sigma_V0), 1e-6)
    
    # Set priors for regularization (default to initial guesses)
    if sigma_V_prior is None:
        sigma_V_prior = sigma_V0
    if V_prior is None:
        V_prior = V0
    
    # Compute bounds for V from leverage constraints
    # leverage = D/V, so V = D/leverage
    # leverage_min <= D/V <= leverage_max
    # => D/leverage_max <= V <= D/leverage_min
    V_min = max(D / leverage_max, 1e-6) if leverage_max > 0 else 1e-6
    V_max = D / leverage_min if leverage_min > 0 else 1e10
    
    # Ensure V_min < V_max and V0 is within bounds
    if V_min >= V_max:
        # If bounds are invalid, use reasonable defaults
        V_min = max(E + D * 0.1, 1e-6)
        V_max = (E + D) * 10.0
    
    # Clip initial guess to bounds
    V0 = np.clip(V0, V_min, V_max)
    sigma_V0 = np.clip(sigma_V0, sigma_V_min, sigma_V_max)
    
    def residuals(params):
        """
        Compute residuals for least squares optimization.
        
        Returns:
        --------
        array
            Residuals: [eq1, eq2, reg_sigma, reg_V]
        """
        V, sigma_V = params
        
        # Ensure parameters are within bounds (will be enforced by optimizer, but good to check)
        V = max(V, V_min)
        V = min(V, V_max)
        sigma_V = max(sigma_V, sigma_V_min)
        sigma_V = min(sigma_V, sigma_V_max)
        
        # Equation 1: Equity value
        E_calc = black_scholes_call(V, D, T, r, sigma_V)
        eq1 = E_calc - E
        
        # Equation 2: Equity volatility
        delta = black_scholes_delta(V, D, T, r, sigma_V)
        E_vol_calc = (delta * sigma_V * V) / E if E > 0 else 0
        eq2 = E_vol_calc - sigma_E_smooth
        
        # Regularization terms
        reg_sigma = np.sqrt(lambda_sigma) * (sigma_V - sigma_V_prior) if lambda_sigma > 0 else 0
        reg_V = np.sqrt(lambda_V) * (V / V_prior - 1) if lambda_V > 0 and V_prior > 0 else 0
        
        return np.array([eq1, eq2, reg_sigma, reg_V])
    
    # Bounds: [V_min, sigma_V_min], [V_max, sigma_V_max]
    bounds = ([V_min, sigma_V_min], [V_max, sigma_V_max])
    
    try:
        # Use least_squares with bounds
        result = least_squares(
            residuals,
            [V0, sigma_V0],
            bounds=bounds,
            method='trf',  # Trust Region Reflective algorithm (supports bounds)
            ftol=1e-6,
            xtol=1e-6,
            max_nfev=5000
        )
        
        V, sigma_V = result.x
        
        # Ensure final values are within bounds
        V = np.clip(V, V_min, V_max)
        sigma_V = np.clip(sigma_V, sigma_V_min, sigma_V_max)
        
        # Ensure positive
        V = max(V, 1e-6)
        sigma_V = max(sigma_V, 1e-6)
        
        return V, sigma_V
        
    except Exception as e:
        # On failure, use standard approximation (clipped to bounds)
        V = np.clip(E + D, V_min, V_max)
        sigma_V = np.clip(
            sigma_E_smooth * E / (E + D) if (E + D) > 0 else sigma_E_smooth,
            sigma_V_min,
            sigma_V_max
        )
        V = max(V, 1e-6)
        sigma_V = max(sigma_V, 1e-6)
        return V, sigma_V


