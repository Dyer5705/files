# Metrics Definitions

## 1D / 5D / 1M Return

**Formula:** `(price_today / price_N_days_ago) - 1`

Expressed as a decimal (0.05 = 5%). Computed from adjusted close prices to account for splits and dividends.

## Cumulative Return

**Formula:** `(price_today / price_on_first_date) - 1`

Shows total return from the beginning of the dataset. Useful for comparing performance across the full period.

## Rolling 20-Day Volatility (Annualized)

**Formula:** `std(daily_returns, window=20) × sqrt(252)`

Standard deviation of daily returns over a rolling 20-day window, annualized by multiplying by the square root of 252 (approximate trading days per year). Higher = more volatile.

## Rolling 60-Day Beta vs. SPY

**Formula:** `cov(stock_returns, SPY_returns) / var(SPY_returns)`

Measures how much the stock moves relative to the S&P 500 (SPY):
- Beta = 1.0 → moves in line with the market
- Beta > 1.0 → more volatile than the market
- Beta < 1.0 → less volatile than the market
- Beta < 0 → moves opposite to the market

## Drawdown

**Formula:** `(price_today - rolling_max_price) / rolling_max_price`

How far the stock is below its most recent peak. Always ≤ 0.
- 0.00 = at all-time high in the period
- -0.20 = 20% below the most recent peak (a 20% drawdown)
