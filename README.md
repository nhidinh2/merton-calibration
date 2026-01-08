# Merton Structural Credit Model Calibration

This project implements and evaluates three approaches to calibrating the Merton (1974) structural credit model for estimating default probabilities from equity market data. The goal is to address the ill-posed inverse problem of estimating unobservable asset values and volatilities from observable equity prices and volatilities.

## Key Results

**Baseline model fails due to extreme sensitivity**: The unconstrained calibration exhibits median elasticity of 9.211 (p95 = 90.445) to equity volatility, causing PD instability with max daily changes in log(PD) ranging from 4.60 to 31.55 across firms.

**EWMA smoothing reduces error by 80-95%**: The improved model (EWMA-smoothed volatility) achieves:
- **80-95% reduction** in PD instability (max |Δlog(PD)|: 0.29-2.31 vs 4.60-31.55 baseline)
- **93% reduction** in risk ranking errors (1.2% wrong sign days vs 17.1% baseline)
- **26% reduction** in median sensitivity to equity volatility (6.790 vs 9.211 baseline)
- **Best overall performance** across all diagnostic dimensions

**Bounded calibration enforces constraints but degrades risk ranking**: While successfully constraining parameters (σ_V ∈ [0.03, 1.2]), the bounded model shows 44% wrong sign days (vs 1.2% improved) and correlation drops to 0.300 (vs 0.700 improved), suggesting hard constraints sacrifice economic consistency.

**Recommendation**: Use improved model (EWMA smoothing) for production. It provides the optimal balance between stability and accuracy.

## Reproducing Results

All results are reproducible with fixed random seeds. To regenerate the complete analysis:

### Step 1: Run All Models

```bash
# Set random seed for reproducibility (if needed)
export PYTHONHASHSEED=42

# Run baseline model
python -m model.naive_model
# Output: outputs/naive_results.csv

# Run improved model (recommended)
python -m model.improved
# Output: outputs/improved_results.csv, outputs/smoothed_volatility.png

# Run bounded model
python -m model.improved --bounded \
  --sigma-v-min 0.03 --sigma-v-max 1.2 \
  --leverage-min 0.05 --leverage-max 0.98 \
  --lambda-sigma 0.2 --lambda-v 0.2
# Output: outputs/bounded_results.csv
```

### Step 2: Generate Comparison Report

```bash
# Compare all models and generate diagnostic report
python -m model.evaluation.compare_all_models
# Generates comprehensive comparison with all metrics
```

### Step 3: View Results

Results are saved to `outputs/`:
- `naive_results.csv` - Baseline model results
- `improved_results.csv` - Improved model results (recommended)
- `bounded_results.csv` - Bounded model results
- Diagnostic plots (PNG files) - Visual comparisons

**Random Seeds**: 
- Sensitivity analysis uses fixed seed `42` (see `model/evaluation/compare_model.py:311`)
- Synthetic data generation uses deterministic seeds based on firm_id hash
- All results are fully reproducible

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd credit_model
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Set up FRED API key for risk-free rate data:
```bash
export FRED_API_KEY=your_key_here
```
Get a free API key from: https://fred.stlouisfed.org/docs/api/api_key.html

### Running the Models

**Baseline (Naive) Model:**
```bash
python -m model.naive_model
# Output: outputs/naive_results.csv
```

**Improved Model (Recommended):**
```bash
python -m model.improved
# Output: outputs/improved_results.csv
# Also generates: outputs/smoothed_volatility.png
```

**Bounded Model:**
```bash
python -m model.improved --bounded \
  --sigma-v-min 0.03 --sigma-v-max 1.2 \
  --leverage-min 0.05 --leverage-max 0.98 \
  --lambda-sigma 0.2 --lambda-v 0.2
# Output: outputs/bounded_results.csv
```

**Compare All Models:**
```bash
python -m model.evaluation.compare_all_models
# Generates comprehensive comparison report
```

## Project Structure

```
credit_model/
├── model/
│   ├── baseline/              # Baseline (naive) model implementation
│   ├── improved/             # Improved model with EWMA smoothing
│   │   ├── calibration.py   # Calibration functions (unconstrained + bounded)
│   │   ├── model.py         # Black-Scholes functions
│   │   ├── smoothing.py     # EWMA volatility smoothing
│   │   └── risk_measures.py # Distance-to-default and PD computation
│   ├── naive_model/         # Alternative baseline implementation
│   └── evaluation/          # Diagnostic and comparison tools
├── data/
│   ├── real/                # Real firm data (2020)
│   ├── synthetic/           # Synthetic test data
│   ├── generate/           # Data generation scripts
│   └── DATA.md             # Data documentation
├── outputs/                 # Results and diagnostic plots
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── FINAL_SUMMARY.md        # Comprehensive project summary
└── progress.md             # Detailed technical documentation
```

## Models Overview

### 1. Baseline (Naive) Model

- **Method**: Unconstrained root-finding using `scipy.optimize.fsolve`
- **Input**: Raw equity volatility from market data
- **Characteristics**: Simple but suffers from high sensitivity and PD instability

### 2. Improved Model (RECOMMENDED)

- **Method**: Unconstrained root-finding with EWMA-smoothed volatility
- **Input**: EWMA-smoothed equity volatility (λ = 0.94)
- **Characteristics**: 
  - Best overall performance
  - 80-95% reduction in PD instability
  - Best risk ranking accuracy (1.2% wrong sign days)
  - Most balanced sensitivity across parameters

### 3. Bounded Model

- **Method**: Constrained nonlinear least squares with bounds and regularization
- **Constraints**: σ_V ∈ [0.03, 1.2], leverage ∈ [0.05, 0.98]
- **Characteristics**: 
  - Enforces parameter bounds
  - Best sensitivity to σ_E
  - Poor risk ranking performance (44% wrong sign days)

## Key Findings

**The Improved Model (EWMA smoothing) provides the best overall performance:**

| Metric | Baseline | Improved | Bounded | Winner |
|--------|----------|----------|---------|--------|
| Risk Ranking (wrong sign %) | 17.1% | **1.2%** | 44.0% | **Improved** |
| PD Stability (avg) | High | **Low** | Mixed | **Improved** |
| Sensitivity Balance | Poor | **Good** | Poor | **Improved** |

See `FINAL_SUMMARY.md` for comprehensive comparison and analysis.

## Data

### Real Firm Data

The project uses 2020 data for five firms:
- **AAPL**: Apple Inc. (Technology)
- **JPM**: JPMorgan Chase & Co. (Financial Services)
- **TSLA**: Tesla Inc. (Automotive/Technology)
- **XOM**: Exxon Mobil Corporation (Energy)
- **F**: Ford Motor Company (Automotive)

### Data Sources

- **Equity prices and volatility**: Yahoo Finance (yfinance)
- **Debt data**: Yahoo Finance balance sheet (annual, forward-filled to daily)
- **Risk-free rates**: FRED API (10-Year Treasury Constant Maturity Rate)

### Generating Real Data

To regenerate real firm data:
```bash
python data/generate/generate_real_data.py
# Or with FRED API key:
export FRED_API_KEY=your_key_here
python data/generate/generate_real_data.py
```

See `data/DATA.md` for detailed data documentation.

## Diagnostic Framework

The project includes a comprehensive diagnostic framework evaluating:

1. **PD Stability**: Maximum daily change in log(PD) per firm
2. **Asset Plausibility**: V/E ratio distributions, invalid value counts
3. **Risk Ranking**: Spearman correlation, wrong-sign days, top-k containment
4. **Sensitivity**: Median and p95 elasticities of log(PD) w.r.t. all inputs

Run diagnostics:
```bash
# Compare all models
python -m model.evaluation.compare_all_models

# Diagnose specific model
python -m model.evaluation.diagnose_naive_model
python -m model.evaluation.compare_model
```

## Dependencies

- `numpy>=1.21.0`: Numerical computations
- `scipy>=1.7.0`: Optimization (`fsolve`, `least_squares`)
- `pandas>=1.3.0`: Data manipulation
- `matplotlib>=3.4.0`: Visualization
- `yfinance>=0.2.0`: Equity data fetching
- `fredapi>=0.5.0`: Risk-free rate data (optional)

## Documentation

- **FINAL_SUMMARY.md**: Comprehensive project summary and findings
- **progress.md**: Detailed technical documentation and methodology
- **model/MODEL.md**: Implementation details for each model component
- **data/DATA.md**: Data sources, formats, and processing details

## Usage Examples

### Basic Usage

```python
from model.improved.calibration import calibrate_asset_parameters
from model.improved.risk_measures import compute_risk_measures
from model.improved.smoothing import smooth_equity_volatility

# Load data
import pandas as pd
equity_vol = pd.read_csv('data/real/equity_vol.csv', parse_dates=['date'])

# Smooth volatility
equity_vol_smooth = smooth_equity_volatility(equity_vol)

# Calibrate for a single observation
E = 1000.0  # Equity in millions
sigma_E = 0.30  # Smoothed equity volatility
D = 500.0  # Debt in millions
T = 1.0  # Time to maturity (years)
r = 0.02  # Risk-free rate

V, sigma_V = calibrate_asset_parameters(E, sigma_E, D, T, r)

# Compute risk measures
risk = compute_risk_measures(V, D, T, r, sigma_V)
print(f"Default Probability: {risk['PD']:.6f}")
print(f"Distance-to-Default: {risk['DD']:.4f}")
```

### Bounded Calibration

```python
from model.improved.calibration import calibrate_asset_parameters_bounded

V, sigma_V = calibrate_asset_parameters_bounded(
    E, sigma_E, D, T, r,
    sigma_V_min=0.03,
    sigma_V_max=1.2,
    leverage_min=0.05,
    leverage_max=0.98,
    lambda_sigma=0.2,
    lambda_V=0.2
)
```

## Limitations

1. **European Option Assumption**: Default only at maturity T, not before
2. **Single Debt Proxy**: Total debt from balance sheet, ignores maturity structure
3. **Constant Parameters**: Asset volatility and drift assumed constant over horizon
4. **Data Limitations**: Annual debt data forward-filled to daily frequency
5. **Time Period**: Single year (2020) analyzed, five firms

## Recommendations

**For Production Use**: Use the **Improved Model (EWMA Smoothing)**. It provides:
- Best risk ranking accuracy
- Most balanced sensitivity
- Best PD stability
- Simple implementation

The bounded model can serve as a fallback when unconstrained solutions produce implausible parameters.

## Future Work

- Extend stress-testing framework across market regimes
- Benchmark against market signals (CDS spreads, credit ratings)
- Explore hybrid approaches combining EWMA smoothing with selective bounds
- Test on additional firms and time periods

## References

- **Merton (1974)**: "On the Pricing of Corporate Debt: The Risk Structure of Interest Rates"
- **Merton Model Calculator**: [Credit Risk Calculator](https://www.creditrisk.nathangs.ca/)

## License

[Add your license here]

## Contact

[Add contact information here]

