# Data Dictionary

## Table: prices_daily

Raw daily price data as received from Yahoo Finance.

| Column | Type | Description |
|---|---|---|
| `date` | TEXT (YYYY-MM-DD) | Trading date |
| `ticker` | TEXT | Stock ticker symbol (e.g., AAPL) |
| `open` | REAL | Opening price |
| `high` | REAL | Intraday high price |
| `low` | REAL | Intraday low price |
| `close` | REAL | Raw closing price |
| `adj_close` | REAL | Adjusted close (accounts for splits & dividends) — **use this for returns** |
| `volume` | INTEGER | Shares traded |
| `source` | TEXT | Always "yfinance" |
| `load_timestamp` | TEXT | When this row was inserted |

Primary Key: `(date, ticker)`

---

## Table: returns_daily

Computed performance and risk metrics. Derived from `prices_daily`.

| Column | Type | Description |
|---|---|---|
| `date` | TEXT | Trading date |
| `ticker` | TEXT | Stock ticker |
| `return_1d` | REAL | Single-day % return (decimal: 0.01 = 1%) |
| `return_5d` | REAL | 5-trading-day return |
| `return_1m` | REAL | ~21 trading day return |
| `cumulative_return` | REAL | Total return from first date in dataset |
| `rolling_vol_20d` | REAL | Annualized rolling 20-day volatility |
| `rolling_beta_60d` | REAL | Rolling 60-day beta vs. SPY |
| `drawdown` | REAL | Drawdown from rolling peak (always ≤ 0) |
| `load_timestamp` | TEXT | When this row was computed |

Primary Key: `(date, ticker)`

---

## Table: data_quality_log

Results from validation checks run by `validate_data.py`.

| Column | Type | Description |
|---|---|---|
| `run_id` | TEXT | Unique ID for a validation run |
| `check_name` | TEXT | Name of the check (e.g., "missing_dates") |
| `status` | TEXT | "PASS" or "FAIL" |
| `details` | TEXT | Human-readable description of result |
| `timestamp` | TEXT | When the check ran |
