# Data Documentation

## Data Files

### Real Firm Data (`data/real/`)

Used for model calibration and evaluation. Contains 2020 data for 5 firms:
- **AAPL**: Apple Inc.
- **JPM**: JPMorgan Chase & Co.
- **TSLA**: Tesla Inc.
- **XOM**: Exxon Mobil Corporation
- **F**: Ford Motor Company

**Files**:
- `equity_prices.csv` - Daily stock prices (1,260 rows)
- `equity_vol.csv` - Daily equity volatility (1,260 rows)
- `debt_quarterly.csv` - Annual debt values (5 rows, one per firm)
- `risk_free.csv` - Daily risk-free rates (262 rows)

**Data Sources**:
- Equity prices/volatility: Yahoo Finance (yfinance)
- Debt: Yahoo Finance balance sheet (annual only)
- Risk-free rates: FRED API (10-Year Treasury) or approximate values

### Synthetic Data (`data/synthetic/`)

Test data with known parameters for validation. Can be regenerated using `data/generate/synthetic_test.py`.

## File Formats

All files are CSV format with the following columns:

### `equity_prices.csv`
- `date`: Trading date (YYYY-MM-DD)
- `firm_id`: Firm ticker (AAPL, JPM, TSLA, XOM, F)
- `equity_price`: Closing stock price (USD per share)

### `equity_vol.csv`
- `date`: Trading date (YYYY-MM-DD)
- `firm_id`: Firm ticker
- `equity_vol`: Annualized equity volatility (decimal, e.g., 0.30 = 30%)

**Note**: Real data uses 30-day rolling realized volatility.

### `debt_quarterly.csv`
- `date`: Year-end date (YYYY-MM-DD)
- `firm_id`: Firm ticker
- `debt`: Total debt in **millions USD**

**Important**: Real debt data is **annual only** (Yahoo Finance limitation). The same annual value is forward-filled to daily frequency in the model.

### `risk_free.csv`
- `date`: Trading date (YYYY-MM-DD)
- `risk_free_rate`: Annualized risk-free rate (decimal, e.g., 0.05 = 5%)

## Data Usage

### Loading Data

```python
import pandas as pd

# Load data
equity_prices = pd.read_csv('data/real/equity_prices.csv', parse_dates=['date'])
equity_vol = pd.read_csv('data/real/equity_vol.csv', parse_dates=['date'])
debt = pd.read_csv('data/real/debt_quarterly.csv', parse_dates=['date'])
risk_free = pd.read_csv('data/real/risk_free.csv', parse_dates=['date'])
```

### Data Alignment

The models handle data alignment automatically:
- **Equity data**: Daily frequency, used directly
- **Debt data**: Annual frequency, forward-filled to daily
- **Risk-free rate**: Daily frequency, used directly

### Equity Market Cap Calculation

Equity prices are per-share. Convert to total market cap (in millions):
```python
shares_outstanding = {
    'AAPL': 16.93,  # billions
    'JPM': 3.09,
    'TSLA': 3.325,
    'XOM': 4.25,
    'F': 3.97
}

# Convert: E_total = price_per_share * shares_billions * 1000 (millions)
E_total = equity_price * shares_outstanding[firm_id] * 1000
```

## Regenerating Data

### Real Data

```bash
# Without FRED API key (uses approximate risk-free rates)
python data/generate/generate_real_data.py

# With FRED API key (for real risk-free rates)
export FRED_API_KEY=your_key_here
python data/generate/generate_real_data.py
```

Get a free FRED API key from: https://fred.stlouisfed.org/docs/api/api_key.html

### Synthetic Data

```bash
python data/generate/synthetic_test.py
```

## Key Limitations

1. **Debt Frequency**: Real debt data is annual only (Yahoo Finance limitation). Forward-filled to daily in models.
2. **Volatility**: Uses realized volatility (30-day rolling), not implied volatility.
3. **Time Period**: Single year (2020) analyzed.
4. **Firm Sample**: Five firms, may not generalize to all sectors.
