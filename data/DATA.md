# Data Documentation

This document describes the data files provided for the structural credit modeling take-home assignment.

## Data Sources

### Synthetic Data (`data/synthetic/`)

The synthetic data is generated using the Merton model with known parameters. This data is only useful for:
- Validating calibration accuracy
- Testing model implementation
- Understanding model behavior with controlled inputs

### Real Firm Data (`data/real/`)

The real firm data is fetched from financial APIs:
- **Equity prices and volatility**: Yahoo Finance (yfinance)
- **Debt data**: Yahoo Finance balance sheet data
- **Risk-free rates**: FRED (Federal Reserve Economic Data) - 10Y Treasury rates


**Note**: For real risk-free rates, you need a free FRED API key from https://fred.stlouisfed.org/docs/api/api_key.html
Set it as an environment variable: `export FRED_API_KEY=your_key_here`

## File Formats

All data files are CSV format with the following structure:

### `equity_prices.csv`

Daily equity prices for each firm.

**Columns**:
- `date`: Trading date (YYYY-MM-DD format)
- `firm_id`: Firm identifier (ticker symbol for real data, FIRM_A/B/C/D/E for synthetic)
- `equity_price`: Closing stock price (USD)

**Frequency**: Daily (business days only)

**Example**:
```csv
date,firm_id,equity_price
2020-01-02,AAPL,75.09
2020-01-03,AAPL,74.36
```

### `equity_vol.csv`

Daily equity volatility estimates.

**Columns**:
- `date`: Trading date (YYYY-MM-DD format)
- `firm_id`: Firm identifier
- `equity_vol`: Annualized equity volatility (decimal, e.g., 0.30 = 30%)

**Frequency**: Daily (business days only)

**Note**: 
- For real data: 30-day rolling realized volatility (annualized)
- For synthetic data: Approximate volatility based on asset volatility and leverage

**Example**:
```csv
date,firm_id,equity_vol
2020-01-02,AAPL,0.2845
2020-01-03,AAPL,0.2851
```

### `debt_quarterly.csv`

Debt values for each firm (annual for real data, quarterly for synthetic).

**Columns**:
- `date`: Date (YYYY-MM-DD format) - year-end for real data, quarter-end for synthetic
- `firm_id`: Firm identifier
- `debt`: Total debt in millions USD

**Frequency**: 
- **Real data**: Annual (year-end dates only) - Yahoo Finance provides annual data only
- **Synthetic data**: Quarterly (end of quarter dates)

**Note**:
- For real data: Total debt from balance sheet. **Yahoo Finance provides annual data only** (year-end values), so there is only one entry per company per year. This is a limitation of the data source - true quarterly debt data would require accessing SEC 10-Q filings directly.
- For synthetic data: Constant debt value (ground truth parameter) provided quarterly
- Debt values are in **millions** of USD
- When aligning to daily frequency, use forward-fill from the annual/quarterly dates

**Example (real data)**:
```csv
date,firm_id,debt
2020-12-31,AAPL,132480.0
```

**Example (synthetic data)**:
```csv
date,firm_id,debt
2020-03-31,FIRM_A,30.0
2020-06-30,FIRM_A,30.0
```

### `risk_free.csv`

Risk-free interest rates.

**Columns**:
- `date`: Trading date (YYYY-MM-DD format)
- `risk_free_rate`: Annualized risk-free rate (decimal, e.g., 0.05 = 5%)

**Frequency**: Daily (business days only)

**Note**:
- For real data: 10-Year Treasury Constant Maturity Rate (from FRED)
- For synthetic data: Constant rate (default: 5%)
- Rates are provided as decimals (not percentages)

**Example**:
```csv
date,risk_free_rate
2020-01-02,0.0180
2020-01-03,0.0181
```

## Data Alignment Rules

When using the data for modeling:

1. **Date Alignment**:
   - Equity data is daily; use the most recent available price/volatility for a given date
   - Debt data is annual (real) or quarterly (synthetic); use forward-fill to align with daily equity data
   - Risk-free rate is daily; use the rate for the specific date

2. **Missing Data**:
   - If equity data is missing for a date, skip that date or use the previous day's value
   - If debt data is missing, use the most recent annual/quarterly value (forward-fill)
   - If risk-free rate is missing, use the most recent available rate

3. **Time to Maturity (T)**:
   - The model assumes a constant time to maturity (typically 1 year)
   - Use the same T value for all firms in a given analysis

## Firms Included

### Real Data Firms

- **AAPL**: Apple Inc. (Technology)
- **JPM**: JPMorgan Chase & Co. (Financial Services)
- **TSLA**: Tesla Inc. (Automotive/Technology)
- **XOM**: Exxon Mobil Corporation (Energy)
- **F**: Ford Motor Company (Automotive)

### Synthetic Data Firms

- **FIRM_A**: Low risk (30% leverage, 15% volatility)
- **FIRM_B**: Medium risk (50% leverage, 25% volatility)
- **FIRM_C**: High risk (60% leverage, 40% volatility)
- **FIRM_D**: Very low risk (20% leverage, 20% volatility)
- **FIRM_E**: Distressed (85% leverage, 35% volatility)

## Data Quality Notes

### Real Data Limitations

1. **Debt Data**: 
   - **Yahoo Finance balance sheets only provide annual data** (year-end values), not quarterly
   - The same annual debt value is used for all four quarters within that year
   - This is a limitation of the free data source - true quarterly data would require accessing SEC 10-Q filings
   - Different firms may report debt differently (total debt vs. long-term debt)
   - For modeling purposes, using annual values for all quarters is a reasonable approximation when quarterly data is unavailable

2. **Equity Volatility**:
   - Realized volatility is calculated from historical returns
   - May differ from implied volatility (which would be preferred but harder to obtain)
   - 30-day rolling window is used for stability

3. **Risk-Free Rate**:
   - 10Y Treasury is a proxy; actual risk-free rate may vary
   - FRED API key required for real-time data (free registration)

### Synthetic Data Characteristics

- All parameters are known (ground truth)
- Data is generated using geometric Brownian motion
- Equity prices and volatilities are derived from asset values using Black-Scholes
- Useful for validating calibration accuracy

## Usage Examples

### Loading Data in Python

```python
import pandas as pd

# Load equity prices
equity_prices = pd.read_csv('data/real/equity_prices.csv', parse_dates=['date'])

# Load debt (quarterly)
debt = pd.read_csv('data/real/debt_quarterly.csv', parse_dates=['date'])

# Forward-fill debt to daily frequency
debt_daily = debt.set_index('date').reindex(
    equity_prices['date'].unique(), 
    method='ffill'
).reset_index()

# Merge with equity data
merged = equity_prices.merge(
    debt_daily, 
    on=['date', 'firm_id'], 
    how='left'
)
```

## Data Generation (For Reference Only)

**Note**: Data is already provided in the repository. You do not need to generate it.

The data generation scripts are available for reference only (with `DELETE_` prefix):
- `baseline/DELETE_synthetic_test.py` - Generates synthetic data
- `baseline/DELETE_generate_real_data.py` - Fetches real data from APIs

These scripts are provided for transparency but are not required for the assignment.

