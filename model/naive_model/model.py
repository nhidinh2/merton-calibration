"""
Merton Structural Credit Model

Implement the baseline Merton (1974) model here.
"""

import numpy as np
from scipy.stats import norm


def black_scholes_d1_d2(S, K, T, r, sigma):
    """
    Calculate d1 and d2 parameters for Black-Scholes formula.
    
    These are intermediate calculations used in all Black-Scholes formulas.
    
    Parameters:
    -----------
    S : float
        Current asset price
    K : float
        Strike price
    T : float
        Time to maturity (in years)
    r : float
        Risk-free rate (annualized)
    sigma : float
        Volatility (annualized)
    
    Returns:
    --------
    tuple (d1, d2)
        d1 and d2 parameters
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        # Return default values for edge cases
        if S > K:
            return (np.inf, np.inf)
        else:
            return (-np.inf, -np.inf)
    
    sqrt_T = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / sqrt_T
    d2 = d1 - sqrt_T
    return d1, d2


def black_scholes_call(S, K, T, r, sigma):
    """
    Black-Scholes formula for European call option price.
    
    Parameters:
    -----------
    S : float
        Current asset price
    K : float
        Strike price
    T : float
        Time to maturity (in years)
    r : float
        Risk-free rate (annualized)
    sigma : float
        Volatility (annualized)
    
    Returns:
    --------
    float
        Call option price
    """

    if T <= 0 or sigma <= 0 or S <= 0:
        return max(S - K * np.exp(-r * T), 0)
    
    d1, d2 = black_scholes_d1_d2(S, K, T, r, sigma)
    call_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return call_price



def black_scholes_delta(S, K, T, r, sigma):
    """
    Delta (sensitivity to underlying price) of Black-Scholes call option.
    
    Delta measures how much the option price changes when the underlying price changes.
    For a call option: delta = ∂E/∂V = Φ(d₁)
    
    Parameters:
    -----------
    S : float
        Current asset price
    K : float
        Strike price
    T : float
        Time to maturity (in years)
    r : float
        Risk-free rate (annualized)
    sigma : float
        Volatility (annualized)
    
    Returns:
    --------
    float
        Delta of the call option (between 0 and 1)
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        return 1.0 if S > K else 0.0
    
    d1, _ = black_scholes_d1_d2(S, K, T, r, sigma)
    delta = norm.cdf(d1)
    return delta


def black_scholes_vega(S, K, T, r, sigma):
    """
    Vega (sensitivity to volatility) of Black-Scholes call option.
    
    Parameters:
    -----------
    S : float
        Current asset price
    K : float
        Strike price
    T : float
        Time to maturity (in years)
    r : float
        Risk-free rate (annualized)
    sigma : float
        Volatility (annualized)
    
    Returns:
    --------
    float
        Vega of the call option
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0.0
    
    d1, _ = black_scholes_d1_d2(S, K, T, r, sigma)
    vega = S * norm.pdf(d1) * np.sqrt(T)
    return vega


def black_scholes_gamma(S, K, T, r, sigma):
    """
    Gamma (second derivative with respect to underlying price) of Black-Scholes call option.
    
    Gamma measures the rate of change of delta with respect to the underlying price.
    For a call option: gamma = ∂²E/∂V² = φ(d₁) / (V * σ * √T)
    
    Parameters:
    -----------
    S : float
        Current asset price
    K : float
        Strike price
    T : float
        Time to maturity (in years)
    r : float
        Risk-free rate (annualized)
    sigma : float
        Volatility (annualized)
    
    Returns:
    --------
    float
        Gamma of the call option
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0.0
    
    d1, _ = black_scholes_d1_d2(S, K, T, r, sigma)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    return gamma


def black_scholes_theta(S, K, T, r, sigma):
    """
    Theta (sensitivity to time decay) of Black-Scholes call option.
    
    Theta measures how much the option price decreases as time passes.
    For a call option: theta = ∂E/∂T (negative for long positions)
    
    Parameters:
    -----------
    S : float
        Current asset price
    K : float
        Strike price
    T : float
        Time to maturity (in years)
    r : float
        Risk-free rate (annualized)
    sigma : float
        Volatility (annualized)
    
    Returns:
    --------
    float
        Theta of the call option (per year, typically negative)
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0.0
    
    d1, d2 = black_scholes_d1_d2(S, K, T, r, sigma)
    
    # Theta formula for call option
    theta = (
        -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
        - r * K * np.exp(-r * T) * norm.cdf(d2)
    )
    return theta


def black_scholes_rho(S, K, T, r, sigma):
    """
    Rho (sensitivity to interest rate) of Black-Scholes call option.
    
    Rho measures how much the option price changes when the risk-free rate changes.
    For a call option: rho = ∂E/∂r = K * T * e^(-r*T) * Φ(d₂)
    
    Parameters:
    -----------
    S : float
        Current asset price
    K : float
        Strike price
    T : float
        Time to maturity (in years)
    r : float
        Risk-free rate (annualized)
    sigma : float
        Volatility (annualized)
    
    Returns:
    --------
    float
        Rho of the call option (per 1% change in interest rate)
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0.0
    
    _, d2 = black_scholes_d1_d2(S, K, T, r, sigma)
    rho = K * T * np.exp(-r * T) * norm.cdf(d2)
    return rho


def black_scholes_intrinsic_value(S, K, option_type='call'):
    """
    Calculate intrinsic value of an option.
    
    Intrinsic value is the value if the option were exercised immediately.
    For call: max(S - K, 0)
    For put: max(K - S, 0)
    
    Parameters:
    -----------
    S : float
        Current asset price
    K : float
        Strike price
    option_type : str
        'call' or 'put'
    
    Returns:
    --------
    float
        Intrinsic value
    """
    if option_type.lower() == 'call':
        return max(S - K, 0)
    elif option_type.lower() == 'put':
        return max(K - S, 0)
    else:
        raise ValueError("option_type must be 'call' or 'put'")


def black_scholes_time_value(S, K, T, r, sigma, option_type='call'):
    """
    Calculate time value of an option.
    
    Time value = Option price - Intrinsic value
    
    Parameters:
    -----------
    S : float
        Current asset price
    K : float
        Strike price
    T : float
        Time to maturity (in years)
    r : float
        Risk-free rate (annualized)
    sigma : float
        Volatility (annualized)
    option_type : str
        'call' or 'put'
    
    Returns:
    --------
    float
        Time value
    """
    if option_type.lower() == 'call':
        option_price = black_scholes_call(S, K, T, r, sigma)
        intrinsic = black_scholes_intrinsic_value(S, K, 'call')
    else:
        # For put, we'd need put price function (not implemented here)
        raise NotImplementedError("Put option not implemented in this model")
    
    return max(option_price - intrinsic, 0)


def black_scholes_all_greeks(S, K, T, r, sigma):
    """
    Calculate all Greeks (sensitivities) for a Black-Scholes call option.
    
    Parameters:
    -----------
    S : float
        Current asset price
    K : float
        Strike price
    T : float
        Time to maturity (in years)
    r : float
        Risk-free rate (annualized)
    sigma : float
        Volatility (annualized)
    
    Returns:
    --------
    dict
        Dictionary containing:
        - 'price': Option price
        - 'delta': Sensitivity to underlying price
        - 'gamma': Second derivative with respect to price
        - 'vega': Sensitivity to volatility
        - 'theta': Sensitivity to time decay (per year)
        - 'rho': Sensitivity to interest rate (per 1% change)
        - 'd1': d1 parameter
        - 'd2': d2 parameter
        - 'intrinsic_value': Intrinsic value
        - 'time_value': Time value
    """
    d1, d2 = black_scholes_d1_d2(S, K, T, r, sigma)
    
    return {
        'price': black_scholes_call(S, K, T, r, sigma),
        'delta': black_scholes_delta(S, K, T, r, sigma),
        'gamma': black_scholes_gamma(S, K, T, r, sigma),
        'vega': black_scholes_vega(S, K, T, r, sigma),
        'theta': black_scholes_theta(S, K, T, r, sigma),
        'rho': black_scholes_rho(S, K, T, r, sigma),
        'd1': d1,
        'd2': d2,
        'intrinsic_value': black_scholes_intrinsic_value(S, K, 'call'),
        'time_value': black_scholes_time_value(S, K, T, r, sigma, 'call')
    }


class MertonModel:
    """
    Baseline Merton structural credit model.
    
    Assumptions:
    - Firm asset value follows geometric Brownian motion
    - Default occurs only at maturity T if V_T < D
    - Equity is a European call option on firm assets
    """
    
    def __init__(self, T=1.0):
        """
        Initialize Merton model.
        
        Parameters:
        -----------
        T : float
            Time to maturity (years)
        """
        self.T = T
    
    def equity_value(self, V, D, r, sigma_V):
        """
        Calculate equity value as call option on assets.
        
        Parameters:
        -----------
        V : float
            Current asset value
        D : float
            Debt face value
        r : float
            Risk-free rate
        sigma_V : float
            Asset volatility
        
        Returns:
        --------
        float
            Equity value
        """

        return black_scholes_call(V, D, self.T, r, sigma_V)
    
    def equity_volatility(self, V, D, r, sigma_V, E):
        """
        Calculate equity volatility from asset volatility.
        
        Parameters:
        -----------
        V : float
            Current asset value
        D : float
            Debt face value
        r : float
            Risk-free rate
        sigma_V : float
            Asset volatility
        E : float
            Equity value
        
        Returns:
        --------
        float
            Equity volatility
        """
        if E <= 0:
            return 0.0
        
        delta = black_scholes_delta(V, D, self.T, r, sigma_V)
        
        sigma_E = (delta * sigma_V * V) / E if E > 0 else 0.0
        return sigma_E

