# =============================================================================
# src/build_metrics.py — Phase 2: Compute KPIs → returns_daily table
# =============================================================================
# What this script does:
#   1. Reads raw prices from `prices_daily` (written by ingest_prices.py)
#   2. Calculates performance & risk metrics for each ticker
#   3. Saves results to the `returns_daily` table
#
# Run AFTER ingest_prices.py.
# Usage: python src/build_metrics.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from datetime import datetime

import config


engine = create_engine(f"sqlite:///{config.DB_PATH}")


def create_returns_table():
    """Create the returns_daily table if it doesn't exist yet."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS returns_daily (
                date              TEXT NOT NULL,
                ticker            TEXT NOT NULL,
                return_1d         REAL,   -- single-day % return
                return_5d         REAL,   -- 5-day (weekly) % return
                return_1m         REAL,   -- ~21 trading day % return
                cumulative_return REAL,   -- return from the very first date in our data
                rolling_vol_20d   REAL,   -- annualized rolling 20-day volatility
                rolling_beta_60d  REAL,   -- rolling 60-day beta vs SPY
                drawdown          REAL,   -- drawdown from rolling peak (always ≤ 0)
                load_timestamp    TEXT,
                PRIMARY KEY (date, ticker)
            )
        """))
        conn.commit()
    print("Table 'returns_daily' is ready.")


def load_prices() -> pd.DataFrame:
    """Load prices from SQLite into a pandas DataFrame."""
    query = "SELECT date, ticker, adj_close FROM prices_daily ORDER BY ticker, date"
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, parse_dates=["date"])
    print(f"Loaded {len(df)} rows from prices_daily.")
    return df


def compute_metrics(prices_df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a long-format DataFrame of (date, ticker, adj_close),
    compute all our KPI columns and return a long-format results DataFrame.
    """

    # ── Pivot to wide format ──────────────────────────────────────────────────
    # We need a matrix where rows = dates, columns = tickers
    # This makes rolling calculations much easier
    wide = prices_df.pivot(index="date", columns="ticker", values="adj_close")
    wide = wide.sort_index()  # make sure dates are in order

    # ── Daily returns ─────────────────────────────────────────────────────────
    # pct_change() computes (today - yesterday) / yesterday
    returns_1d = wide.pct_change()

    # ── Multi-period returns ──────────────────────────────────────────────────
    returns_5d = wide.pct_change(periods=5)   # ~1 week
    returns_1m = wide.pct_change(periods=21)  # ~1 month

    # ── Cumulative return from start ─────────────────────────────────────────
    # (current price / first price) - 1
    cumulative = wide.div(wide.iloc[0]) - 1

    # ── Rolling volatility (annualized) ──────────────────────────────────────
    # Volatility = std of daily returns × sqrt(252)
    # 252 = approximate trading days in a year
    rolling_vol = (
        returns_1d
        .rolling(window=config.ROLLING_VOL_WINDOW, min_periods=10)
        .std()
        * np.sqrt(252)
    )

    # ── Rolling beta vs SPY ───────────────────────────────────────────────────
    # Beta measures how much a stock moves relative to the market.
    # Beta = cov(stock, SPY) / var(SPY)
    # We calculate it in a rolling window of 60 days.
    spy_returns = returns_1d[config.BENCHMARK] if config.BENCHMARK in returns_1d.columns else None

    rolling_beta = pd.DataFrame(index=wide.index, columns=wide.columns, dtype=float)
    if spy_returns is not None:
        for ticker in wide.columns:
            stock_returns = returns_1d[ticker]
            # zip the two series together and roll through 60-day windows
            combined = pd.concat([stock_returns, spy_returns], axis=1)
            combined.columns = ["stock", "spy"]
            # Compute rolling beta using rolling cov / rolling var
            roll_cov = stock_returns.rolling(config.ROLLING_BETA_WINDOW, min_periods=30).cov(spy_returns)
            roll_var = spy_returns.rolling(config.ROLLING_BETA_WINDOW, min_periods=30).var()
            rolling_beta[ticker] = roll_cov / roll_var

    # ── Drawdown ─────────────────────────────────────────────────────────────
    # Drawdown = how far below the rolling peak we currently are
    # Always ≤ 0. -0.20 means we're 20% below the most recent high.
    rolling_max = wide.cummax()  # the highest price seen up to each date
    drawdown = (wide - rolling_max) / rolling_max

    # ── Combine all metrics back to long format ───────────────────────────────
    # Each metric is a wide DataFrame. We'll melt each one then merge them.
    def melt_metric(df_wide, col_name):
        return (
            df_wide
            .reset_index()
            .melt(id_vars="date", var_name="ticker", value_name=col_name)
        )

    metrics = (
        melt_metric(returns_1d,   "return_1d")
        .merge(melt_metric(returns_5d,   "return_5d"),   on=["date", "ticker"])
        .merge(melt_metric(returns_1m,   "return_1m"),   on=["date", "ticker"])
        .merge(melt_metric(cumulative,   "cumulative_return"), on=["date", "ticker"])
        .merge(melt_metric(rolling_vol,  "rolling_vol_20d"),   on=["date", "ticker"])
        .merge(melt_metric(rolling_beta, "rolling_beta_60d"),  on=["date", "ticker"])
        .merge(melt_metric(drawdown,     "drawdown"),          on=["date", "ticker"])
    )

    metrics["date"] = pd.to_datetime(metrics["date"]).dt.strftime("%Y-%m-%d")
    metrics["load_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return metrics


def save_metrics(metrics_df: pd.DataFrame):
    """Write the computed metrics to the returns_daily table."""
    with engine.connect() as conn:
        metrics_df.to_sql("returns_daily_staging", conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT OR REPLACE INTO returns_daily
            SELECT * FROM returns_daily_staging
        """))
        conn.execute(text("DROP TABLE IF EXISTS returns_daily_staging"))
        conn.commit()
    print(f" Saved {len(metrics_df)} rows to 'returns_daily'.")


# ── Main entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 2 — Metrics Computation")
    print("=" * 60)

    create_returns_table()

    prices = load_prices()

    if prices.empty:
        print(" No prices found. Run ingest_prices.py first!")
    else:
        print("\n⚙️  Computing metrics (this may take a moment)...")
        metrics = compute_metrics(prices)
        print(f"   Computed metrics for {metrics['ticker'].nunique()} tickers "
              f"across {metrics['date'].nunique()} dates.")
        save_metrics(metrics)

    print("\n Done! Metrics are ready for the dashboard.")