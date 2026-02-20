# =============================================================================
# config.py — Central settings for the entire project
# =============================================================================
# Edit this file to change which tickers to track, the date range, etc.
# Everything else in the project reads from here, so you only change things once.

import os

# ── Tickers ──────────────────────────────────────────────────────────────────
# SPY is our benchmark (the S&P 500 ETF). It's used to calculate beta.
BENCHMARK = "SPY"

# These are the stocks we're tracking. Add or remove tickers freely.
TICKERS = [
    "SPY",   # S&P 500 benchmark
    "AAPL",  # Apple
    "MSFT",  # Microsoft
    "AMZN",  # Amazon
    "NVDA",  # Nvidia
    "META",  # Meta
    "GOOGL", # Alphabet
    "JPM",   # JPMorgan
    "XOM",   # ExxonMobil
    "JNJ",   # Johnson & Johnson
    "PG",    # Procter & Gamble
]

# ── Date Range ────────────────────────────────────────────────────────────────
# How far back should we pull historical data?
# "2y" = 2 years of history. Other options: "1y", "6mo", "3mo"
HISTORY_PERIOD = "2y"

# ── Database ──────────────────────────────────────────────────────────────────
# SQLite database file — stored in the data/ folder
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "market_reporting.db")

# ── Metric Parameters ─────────────────────────────────────────────────────────
ROLLING_VOL_WINDOW   = 20   # days for rolling volatility calculation
ROLLING_BETA_WINDOW  = 60   # days for rolling beta calculation
RETURN_SANITY_LIMIT  = 0.30 # flag any single-day return > ±30% as suspicious
