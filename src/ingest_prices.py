# =============================================================================
# src/ingest_prices.py — Phase 1: Pull prices from yfinance → SQLite
# =============================================================================
# What this script does:
#   1. Downloads historical daily OHLCV price data from Yahoo Finance
#   2. Cleans and standardizes column names
#   3. Saves the data into the `prices_daily` table in our SQLite database
#
# Run this script first, before anything else.
# Usage: python src/ingest_prices.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # lets us import config.py

import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

import config  # our central settings file


# ── Step 1: Set up the database connection ────────────────────────────────────
# SQLAlchemy is a library that lets Python talk to SQL databases.
# "sqlite:///" just means "use a local SQLite file at this path"
engine = create_engine(f"sqlite:///{config.DB_PATH}")


def create_tables():
    """
    Create the database tables if they don't already exist.
    'IF NOT EXISTS' means running this twice is safe — it won't overwrite data.
    """
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prices_daily (
                date           TEXT NOT NULL,
                ticker         TEXT NOT NULL,
                open           REAL,
                high           REAL,
                low            REAL,
                close          REAL,
                adj_close      REAL,
                volume         INTEGER,
                source         TEXT DEFAULT 'yfinance',
                load_timestamp TEXT,
                PRIMARY KEY (date, ticker)   -- ensures no duplicate rows
            )
        """))
        conn.commit()
    print(" Table 'prices_daily' is ready.")


def fetch_and_save_prices(tickers: list, period: str):
    """
    Download price data for a list of tickers and save to the database.

    Parameters:
        tickers : list of ticker symbols, e.g. ["AAPL", "MSFT", "SPY"]
        period  : how far back to go, e.g. "2y" for 2 years
    """
    print(f"\n Downloading data for {len(tickers)} tickers ({period} of history)...")

    # yfinance can download multiple tickers at once — very convenient
    raw = yf.download(
        tickers=tickers,
        period=period,
        auto_adjust=False,   # keep both 'Close' and 'Adj Close'
        progress=True,
        group_by="ticker",   # organize results by ticker
    )

    if raw.empty:
        print("No data returned from yfinance. Check your internet connection.")
        return

    load_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # timestamp for auditing
    all_rows = []  # we'll collect all rows here, then insert in one go

    for ticker in tickers:
        try:
            # When downloading multiple tickers, yfinance nests the data
            # We pull out each ticker's slice like this:
            if len(tickers) == 1:
                df = raw.copy()
            else:
                df = raw[ticker].copy()

            df = df.dropna(how="all")  # drop completely empty rows

            # Rename columns to match our database schema
            df = df.rename(columns={
                "Open":      "open",
                "High":      "high",
                "Low":       "low",
                "Close":     "close",
                "Adj Close": "adj_close",
                "Volume":    "volume",
            })

            # Add metadata columns
            df["ticker"]         = ticker
            df["source"]         = "yfinance"
            df["load_timestamp"] = load_ts

            # Convert the index (dates) into a plain column
            df = df.reset_index()
            df = df.rename(columns={"Date": "date", "Datetime": "date"})
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

            # Keep only the columns our table expects
            df = df[["date", "ticker", "open", "high", "low", "close",
                      "adj_close", "volume", "source", "load_timestamp"]]

            all_rows.append(df)
            print(f"  ✔ {ticker}: {len(df)} rows")

        except Exception as e:
            print(f"    Skipping {ticker} — error: {e}")

    if not all_rows:
        print(" No data to save.")
        return

    # Combine all tickers into one DataFrame and insert into SQLite
    combined = pd.concat(all_rows, ignore_index=True)

    # "replace" means: if rows for these (date, ticker) combos already exist,
    # overwrite them. This makes the script safe to re-run.
    with engine.connect() as conn:
        # We use INSERT OR REPLACE to handle the primary key constraint
        combined.to_sql("prices_daily_staging", conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT OR REPLACE INTO prices_daily
            SELECT * FROM prices_daily_staging
        """))
        conn.execute(text("DROP TABLE IF EXISTS prices_daily_staging"))
        conn.commit()

    print(f"\n✅ Saved {len(combined)} total rows to 'prices_daily'.")


# ── Main entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 — Price Ingestion")
    print("=" * 60)

    create_tables()
    fetch_and_save_prices(config.TICKERS, config.HISTORY_PERIOD)

    print("\n Done! Check your data/ folder for market_reporting.db")
