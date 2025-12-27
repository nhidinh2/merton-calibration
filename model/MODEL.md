## `model.py`

### `black_scholes_d1_d2(S, K, T, r, sigma)`

- **What it does**: Calculates the intermediate parameters $d_1$ and $d_2$ used in all Black-Scholes formulas.
- **How it works**:
  - If $T \le 0$, $\sigma \le 0$, or $S \le 0$, returns edge case values based on moneyness.
  - Otherwise computes:
    - $d_1 = \frac{\ln(S/K) + (r + 0.5\sigma^2)T}{\sigma \sqrt{T}}$
    - $d_2 = d_1 - \sigma\sqrt{T}$
- **Inputs**: Same as `black_scholes_call`.
- **Output**:
  - `(d1, d2)`: Tuple of d1 and d2 parameters.

---

### `black_scholes_call(S, K, T, r, sigma)`

- **What it does**: Computes the **Black–Scholes price** of a European call option.
- **How it works**:
  - If $T \le 0$, $\sigma \le 0$, or $S \le 0$, it falls back to intrinsic value:  
    $\max(S - K e^{-rT}, 0)$ (discounted strike, still using $T$ in the discount).
  - Otherwise it computes:
    - $d_1 = \frac{\ln(S/K) + (r + 0.5\sigma^2)T}{\sigma \sqrt{T}}$
    - $d_2 = d_1 - \sigma\sqrt{T}$
    - $C = S \Phi(d_1) - K e^{-rT} \Phi(d_2)$
- **Inputs**:
  - `S`: Current underlying asset price.
  - `K`: Strike price.
  - `T`: Time to maturity in years.
  - `r`: Annual risk-free rate (continuously compounded).
  - `sigma`: Annual volatility of the underlying.
- **Output**:
  - `C`: Theoretical call option price.

---

### `black_scholes_delta(S, K, T, r, sigma)`

- **What it does**: Computes **delta**, i.e. the sensitivity of the call price to the underlying asset price, $\partial C / \partial S$.
- **How it works**:
  - If $T \le 0$, $\sigma \le 0$, or $S \le 0$, returns a simple in/out-of-the-money proxy: `1.0` if $S > K$ else `0.0`.
  - Otherwise:
    - $d_1$ as in `black_scholes_call`.
    - $\Delta = \Phi(d_1)$, where $\Phi$ is the standard normal CDF.
- **Inputs**: Same as `black_scholes_call`.
- **Output**:
  - $\Delta$: Delta of the call option (between 0 and 1).

---

### `black_scholes_vega(S, K, T, r, sigma)`

- **What it does**: Computes **vega**, i.e. the sensitivity of the call price to volatility, $\partial C / \partial \sigma$.
- **How it works**:
  - If $T \le 0$, $\sigma \le 0$, or $S \le 0$, returns 0.0 (no meaningful volatility exposure).
  - Otherwise:
    - $d_1$ as above.
    - $\nu = S \phi(d_1) \sqrt{T}$
- **Inputs**: Same as `black_scholes_call`.
- **Output**:
  - `v`: Vega of the call.

---

### `black_scholes_gamma(S, K, T, r, sigma)`

- **What it does**: Computes **gamma**, i.e. the second derivative of the call price with respect to the underlying price, $\partial^2 C / \partial S^2$.
- **How it works**:
  - If $T \le 0$, $\sigma \le 0$, or $S \le 0$, returns 0.0.
  - Otherwise:
    - $d_1$ as above.
    - $\Gamma = \frac{\phi(d_1)}{S \sigma \sqrt{T}}$
- **Inputs**: Same as `black_scholes_call`.
- **Output**:
  - `gamma`: Gamma of the call option.

---

### `black_scholes_theta(S, K, T, r, sigma)`

- **What it does**: Computes **theta**, i.e. the sensitivity of the call price to time decay, $\partial C / \partial T$.
- **How it works**:
  - If $T \le 0$, $\sigma \le 0$, or $S \le 0$, returns 0.0.
  - Otherwise:
    - $d_1$ and $d_2$ as above.
    - $\Theta = -\frac{S \phi(d_1) \sigma}{2\sqrt{T}} - r K e^{-rT} \Phi(d_2)$
- **Inputs**: Same as `black_scholes_call`.
- **Output**:
  - `theta`: Theta of the call option (per year, typically negative).

---

### `black_scholes_rho(S, K, T, r, sigma)`

- **What it does**: Computes **rho**, i.e. the sensitivity of the call price to the risk-free interest rate, $\partial C / \partial r$.
- **How it works**:
  - If $T \le 0$, $\sigma \le 0$, or $S \le 0$, returns 0.0.
  - Otherwise:
    - $d_2$ as above.
    - $\rho = K T e^{-rT} \Phi(d_2)$
- **Inputs**: Same as `black_scholes_call`.
- **Output**:
  - `rho`: Rho of the call option (per 1% change in interest rate).

---

### `black_scholes_intrinsic_value(S, K, option_type='call')`

- **What it does**: Calculates the **intrinsic value** of an option, i.e. the value if exercised immediately.
- **How it works**:
  - For call: $\max(S - K, 0)$
  - For put: $\max(K - S, 0)$
- **Inputs**:
  - `S`: Current underlying asset price.
  - `K`: Strike price.
  - `option_type`: 'call' or 'put' (default: 'call').
- **Output**:
  - Intrinsic value of the option.

---

### `black_scholes_time_value(S, K, T, r, sigma, option_type='call')`

- **What it does**: Calculates the **time value** of an option, i.e. the difference between option price and intrinsic value.
- **How it works**:
  - Time value = Option price - Intrinsic value
  - For call options: Uses `black_scholes_call()` and `black_scholes_intrinsic_value()`.
- **Inputs**: Same as `black_scholes_call`, plus `option_type`.
- **Output**:
  - Time value of the option.

---

### `black_scholes_all_greeks(S, K, T, r, sigma)`

- **What it does**: Computes **all Greeks and parameters** for a Black-Scholes call option in a single function call.
- **How it works**:
  - Calls all individual Greek functions and returns a comprehensive dictionary.
- **Inputs**: Same as `black_scholes_call`.
- **Output**:
  - Dictionary with keys:
    - `'price'`: Option price
    - `'delta'`: Sensitivity to underlying price
    - `'gamma'`: Second derivative with respect to price
    - `'vega'`: Sensitivity to volatility
    - `'theta'`: Sensitivity to time decay (per year)
    - `'rho'`: Sensitivity to interest rate (per 1% change)
    - `'d1'`: d1 parameter
    - `'d2'`: d2 parameter
    - `'intrinsic_value'`: Intrinsic value
    - `'time_value'`: Time value

---

### `class MertonModel`

Represents the **baseline Merton structural credit model**, where equity is modeled as a call option on firm assets.

#### `__init__(self, T=1.0)`

- **What it does**: Stores the **time to maturity**
- **Inputs**:
  - `T`: time to debt maturity in years (default 1.0).
- **Effect**:
  - Sets `self.T = T`.

---

#### `equity_value(self, V, D, r, sigma_V)`

- **What it does**: Computes the **equity value** given asset value and volatility, by treating equity as a call on assets with strike equal to debt.
- **How it works**:
  - $E = C$ with: 
    - `V` is underlying asset price.
    - `D` is strike price. 
- **Inputs**:
  - `V`: Asset value.
  - `D`: Debt face value.
  - `r`: Risk-free rate.
  - `sigma_V`: Asset volatility.
- **Output**:
  - `E`: model-implied equity value.

---

#### `equity_volatility(self, V, D, r, sigma_V, E)`

- **What it does**: Computes **equity volatility** implied by asset volatility and leverage, using the Merton relationship.
- **Key relationship**:
  - $\sigma_E E = \Delta \sigma_V V$, where:
    - $\sigma_E$: equity volatility,
    - $\Delta = \Phi(d_1)$ is the **equity delta** w.r.t. asset value.
  - So $\sigma_E = \dfrac{\Delta \sigma_V V}{E}$.
- **How it works**:
  - If `E <= 0`, returns `0.0` (no volatility defined for non-positive equity).
  - Computes $\Delta$ then applies the relationship:
    - `sigma_E = (delta * sigma_V * V) / E`.
- **Inputs**:
  - `V`: Asset value.
  - `D`: Debt face value.
  - `r`: Risk-free rate.
  - `sigma_V`: Asset volatility.
  - `E`: Equity value.
- **Output**:
  - `sigma_E`: Equity volatility. 

---

## `calibration.py`

### `calibrate_asset_parameters(E, sigma_E, D, T, r, V0=None, sigma_V0=None)`

- **What it does**: Calibrates **unobservable asset value (V)** and **asset volatility (sigma_V)** from observable equity data ($E$,  $\sigma_E$)  by solving a system of two equations.
- **How it works**:
  1. **Initial guesses**: If not provided, sets:
     - $V_0 = E + D$ (simple approximation: assets = equity + debt)
     - $\sigma_{V0} = \frac{\sigma_E \cdot E}{E + D}$ (leverage-adjusted volatility estimate)
  2. **System of equations**: Defines an inner function `equations(params)` to compute two equations:
     - **Equation 1**: $E = \text{BlackScholes}(V, D, T, r, \sigma_V)$
       - Computes the theoretical equity value using Black-Scholes.
       - Residual: `eq1 = E_calc - E` (should be zero at solution).
     - **Equation 2**: $\sigma_E \cdot E = \Delta \cdot \sigma_V \cdot V$
       - Computes option delta $\Delta$ (sensitivity of equity to asset value).
       - Computes theoretical equity volatility: `E_vol_calc = (delta * sigma_V * V) / E`.
       - Residual: `eq2 = E_vol_calc - sigma_E` (should be zero at solution).
  3. **Numerical solving**: Uses `scipy.optimize.fsolve` to find $V$ and $\sigma_V$ such that both residuals are zero.
  4. **Edge cases**:
     - Ensures $V \geq 10^{-6}$ and $\sigma_V \geq 10^{-6}$ (prevents negative values)
     - If calibration fails (exception), returns initial guesses as fallback
- **Inputs**:
  - `E`: Equity value.
  - `sigma_E`: Equity volatility (raw for naive model, smoothed for improved model).
  - `D`: Debt face value.
  - `T`: Time to maturity in years.
  - `r`: Risk-free rate.
  - `V0`: Initial guess for asset value (default: E + D).
  - `sigma_V0`: Initial guess for asset volatility.
- **Output**:
  - `(V, sigma_V)`: Estimated asset value and asset volatility.

**Note**: In the improved model, this function is called with `sigma_E_smooth` (smoothed equity volatility) instead of raw `sigma_E`.

---

## `risk_measures.py`

### `distance_to_default(V, D, T, r, sigma_V)`

- **What it does**: Calculates **Distance-to-Default (DD)** using the Merton model formula.
- **Interpretation**: Higher DD = lower default risk. DD measures how many standard deviations (in log-space) the asset value is above the default threshold.
- **How it works**:
  - In the Merton model, **DD = -d₂**, where d₂ is the standard Black-Scholes parameter.
  - **Formula**: 
    $\text{DD} = -\frac{\ln(V/D) + (r - 0.5\sigma_V^2)T}{\sigma_V \sqrt{T}}$
  - This is equivalent to: $\text{DD} = \frac{\ln(V/D) + (r - 0.5\sigma_V^2)T}{\sigma_V \sqrt{T}}$ with a sign flip.
  - **Relationship to PD**: $\text{PD} = \Phi(-\text{DD}) = \Phi(d_2)$
  - **Edge cases**:
    - If $T \leq 0$, $\sigma_V \leq 0$, $V \leq 0$, or $D \leq 0$, returns `inf` if $V > D$ else `-inf`
- **Inputs**:
  - `V`: Current asset value.
  - `D`: Debt face value.
  - `T`: Time to maturity in years.
  - `r`: Risk-free rate.
  - `sigma_V`: Asset volatility.
- **Output**:
  - Distance-to-default (DD = -d₂)

---

### `default_probability(V, D, T, r, sigma_V)`

- **What it does**: Calculates the **risk-neutral default probability (PD)**, i.e., the probability that asset value at maturity will be below the debt face value.
- **How it works**:
  - Under the Merton model, asset value at maturity $V_T$ is lognormally distributed
  - Default occurs if $V_T < D$
  - **Formula**: 
    $\text{PD} = \Phi(-d_2)$
    where:
    $d_2 = \frac{\ln(V/D) + (r - \sigma_V^2/2)T}{\sigma_V \sqrt{T}}$
  - **Edge cases**:
    - If $T \leq 0$, $\sigma_V \leq 0$, $V \leq 0$, or $D \leq 0$:
      - Returns `1.0` if $V < D$ (already in default), else `0.0`
    - Clamps result to $[0, 1]$ to ensure valid probability
- **Inputs**:
  - `V`: Asset value.
  - `D`: Debt face value.
  - `T`: Time to maturity in years.
  - `r`: Risk-free rate.
  - `sigma_V`: Asset volatility.
- **Output**:
  - Default probability between 0 and 1

---

### `compute_risk_measures(V, D, T, r, sigma_V)`

- **What it does**: Computes **Distance-to-Default** and **Default Probability**
- **How it works**:
  - Calls `distance_to_default()` and `default_probability()` 
- **Inputs**: Same as `distance_to_default` and `default_probability`
- **Output**:
  - Dictionary with keys:
    - `'DD'`: Distance-to-default
    - `'PD'`: Default probability

---

## `__main__.py` (Baseline Model)

### `main()`

- **What it does**: Main entry point that orchestrates the entire baseline Merton model pipeline: loads data, aligns it, calibrates parameters for each firm/date, computes risk measures, and saves results.
- **How it works**:
  1. **Data Loading**:
     - Loads four CSV files from `data/real/`:
       - `equity_prices.csv`: Daily equity prices per firm (per-share, in dollars)
       - `equity_vol.csv`: Daily equity volatility per firm (annualized)
       - `debt_quarterly.csv`: Quarterly debt values per firm (in millions)
       - `risk_free.csv`: Daily risk-free rates (annualized)
  
  2. **Data Alignment**:
     - **Debt alignment**: For each firm, aligns quarterly debt data to daily equity dates:
       - Creates a combined date index from both equity and debt dates
       - Uses backward-fill then forward-fill to interpolate quarterly debt to daily frequency
       - Filters to only equity trading dates
     - **Equity conversion**: Converts per-share equity prices to total market capitalization:
       - Uses firm-specific shares outstanding (in billions)
       - Formula: $E_{\text{total}} = E_{\text{per-share}} \times \text{shares} \times 1000$ (converts to millions)
     - **Risk-free rate**: Uses daily risk-free rates, aligned by date
  
  3. **Calibration Loop**:
     - For each firm and each date:
       - Extracts equity value (E), equity volatility (σ_E), debt (D), and risk-free rate (r)
       - Uses warm-start initialization: if previous period's solution exists, uses it as initial guess; otherwise uses standard approximation ($V_0 = E + D$, $\sigma_{V0} = \sigma_E \cdot E / (E + D)$)
       - Calls `calibrate_asset_parameters()` to solve for asset value (V) and asset volatility (σ_V)
       - Computes risk measures (DD, PD) using `compute_risk_measures()`
       - Stores results with date, firm_id, V, sigma_V, DD, PD
  
  4. **Output**:
     - Converts results list to pandas DataFrame
     - Creates `outputs/` directory if it doesn't exist
     - Saves results to `outputs/naive_results.csv` with columns:
       - `date`: Evaluation date
       - `firm_id`: Firm identifier
       - `V`: Estimated asset value (in millions)
       - `sigma_V`: Estimated asset volatility (annualized)
       - `DD`: Distance-to-default
       - `PD`: Default probability
     - Prints summary statistics and total observation count
- **Inputs**: None (reads from data files)
- **Output**: 
  - CSV file: `outputs/naive_results.csv`
  - Console output: Progress messages and summary statistics

---

## `smoothing.py` (Improved Model Only)

### `smooth_equity_volatility(equity_vol_df, lambda_ewma=0.94)`

- **What it does**: Smooths noisy realized equity volatility using **Exponentially Weighted Moving Average (EWMA)** on variance, then takes the square root to get smoothed volatility.
- **Rationale**: Raw realized volatility can be very noisy, leading to unstable calibration results. Smoothing reduces noise while preserving the underlying volatility dynamics.
- **How it works**:
  1. For each firm separately:
     - Sorts volatility data by date
     - Applies EWMA smoothing on **variance** (not volatility directly):
       - Initializes with first variance: $\text{var}_{\text{smooth},0} = \sigma_0^2$
       - For each subsequent period: $\text{var}_{\text{smooth},t} = \lambda \cdot \text{var}_{\text{smooth},t-1} + (1-\lambda) \cdot \sigma_t^2$
       - Converts back to volatility: $\sigma_{\text{smooth},t} = \sqrt{\text{var}_{\text{smooth},t}}$
  2. Returns DataFrame with both raw and smoothed volatility columns
- **Parameters**:
  - `equity_vol_df`: DataFrame with columns `date`, `firm_id`, `equity_vol`
  - `lambda_ewma`: EWMA smoothing parameter (default: 0.94, typical for volatility smoothing)
- **Output**:
  - DataFrame with columns: `date`, `firm_id`, `equity_vol_raw`, `equity_vol_smooth`, `equity_vol` (where `equity_vol` is set to smoothed values for pipeline use)

---

### `plot_smoothed_volatility(equity_vol_df, output_path=None)`

- **What it does**: Creates visualization comparing raw vs smoothed equity volatility for each firm.
- **How it works**:
  - Creates subplots (one per firm)
  - Plots raw volatility as light blue line (alpha=0.6)
  - Plots smoothed volatility as dark blue line (linewidth=2)
  - Adds labels, title, legend, and grid
- **Parameters**:
  - `equity_vol_df`: DataFrame with `equity_vol_raw` and `equity_vol_smooth` columns
  - `output_path`: Optional path to save the plot (default: displays interactively)
- **Output**:
  - Saves plot to `outputs/smoothed_volatility.png` if path provided, otherwise displays

---

## `__main__.py` (Improved Model)

### `main()`

- **What it does**: Main entry point for the improved model, which adds volatility smoothing before calibration.
- **How it works**:
  1. **Data Loading**: Same as baseline model
  
  2. **Volatility Smoothing** (NEW):
     - Calls `smooth_equity_volatility()` to apply EWMA smoothing to equity volatility
     - Generates visualization plot saved to `outputs/smoothed_volatility.png`
     - Uses smoothed volatility (`equity_vol_smooth`) for all subsequent calibration steps
  
  3. **Data Alignment**: Same as baseline model
  
  4. **Calibration Loop**: Same as baseline model, but uses smoothed equity volatility (`sigma_E_smooth`) instead of raw volatility
  
  5. **Output**:
     - Saves results to `outputs/improved_results.csv` (same format as baseline)
     - Also saves volatility smoothing plot to `outputs/smoothed_volatility.png`
- **Key Difference from Baseline**: The improved model smooths equity volatility before calibration, which reduces noise and improves stability of asset value and volatility estimates.

---

## Model Comparison

### Baseline (Naive) Model
- Uses **raw equity volatility** directly from data
- Simpler pipeline, no preprocessing
- May suffer from noise-induced instability in calibration

### Improved Model
- **Pre-processes equity volatility** using EWMA smoothing
- Reduces noise in volatility input, leading to more stable calibration
- Same core Merton model structure, only the input volatility is smoothed
- Minimal change: only adds one preprocessing step

---

## References

- **Merton model and calibration write-up**: [Merton Model Credit Risk Calculator](https://www.creditrisk.nathangs.ca/)
- **EWMA Volatility Smoothing**: Common practice in financial modeling to reduce noise in realized volatility estimates
