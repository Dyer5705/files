# 📈 Market Performance & Risk Dashboard

An enterprise-style financial reporting pipeline built with Python, SQLite, and Streamlit.

Ingests daily market data from Yahoo Finance, computes performance and risk KPIs,
stores everything in a structured SQL database, and serves an interactive dashboard.

---

## Project Structure

```
market_dashboard/
├── config.py                  # Central settings (tickers, periods, DB path)
├── requirements.txt           # Python dependencies
│
├── src/
│   ├── ingest_prices.py       # Phase 1: Pull raw prices → SQLite
│   ├── build_metrics.py       # Phase 2: Compute KPIs → SQLite
│   └── validate_data.py       # Phase 3: Data quality checks (coming soon)
│
├── dashboards/
│   └── app.py                 # Streamlit dashboard
│
├── data/
│   └── market_reporting.db    # SQLite database (auto-created)
│
└── docs/
    ├── data_dictionary.md     # Column definitions
    └── metrics_definitions.md # How each KPI is calculated
```

---

## Quickstart

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Pull price data
```bash
python src/ingest_prices.py
```

### 3. Compute metrics
```bash
python src/build_metrics.py
```

### 4. Launch the dashboard
```bash
streamlit run dashboards/app.py
```

---

## Database Tables

| Table | Description |
|---|---|
| `prices_daily` | Raw OHLCV prices from yfinance |
| `returns_daily` | Computed KPIs: returns, volatility, beta, drawdown |
| `data_quality_log` | Validation check results (Phase 3) |

---

## KPIs Included

**Performance**
- 1D / 5D / 1M return
- Cumulative return vs. SPY

**Risk**
- Rolling 20-day annualized volatility
- Rolling 60-day beta vs. SPY
- Drawdown from rolling peak

---

## Configuration

Edit `config.py` to change:
- Which tickers to track (`TICKERS`)
- How much history to pull (`HISTORY_PERIOD`)
- Rolling window sizes
