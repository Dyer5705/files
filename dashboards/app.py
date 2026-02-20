# =============================================================================
# dashboards/app.py — Streamlit Dashboard
# =============================================================================
# Usage: streamlit run dashboards/app.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine

import config

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Market Performance Dashboard",
    page_icon="📈",
    layout="wide",
)

engine = create_engine(f"sqlite:///{config.DB_PATH}")


@st.cache_data(ttl=300)  # cache for 5 minutes so the dashboard stays fast
def load_returns():
    with engine.connect() as conn:
        return pd.read_sql(
            "SELECT * FROM returns_daily ORDER BY date, ticker",
            conn,
            parse_dates=["date"]
        )


@st.cache_data(ttl=300)
def load_prices():
    with engine.connect() as conn:
        return pd.read_sql(
            "SELECT * FROM prices_daily ORDER BY date, ticker",
            conn,
            parse_dates=["date"]
        )


# ── Load data ─────────────────────────────────────────────────────────────────
try:
    returns_df = load_returns()
    prices_df  = load_prices()
    data_loaded = True
except Exception as e:
    data_loaded = False
    error_msg = str(e)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Filters")

if data_loaded and not returns_df.empty:
    available_tickers = sorted(returns_df["ticker"].unique().tolist())
    selected_tickers  = st.sidebar.multiselect(
        "Select Tickers",
        options=available_tickers,
        default=available_tickers[:5],  # default: first 5
    )

    min_date = returns_df["date"].min().date()
    max_date = returns_df["date"].max().date()
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    # Apply filters
    mask = (
        returns_df["ticker"].isin(selected_tickers) &
        (returns_df["date"].dt.date >= start_date) &
        (returns_df["date"].dt.date <= end_date)
    )
    filtered = returns_df[mask].copy()

st.sidebar.markdown("---")
st.sidebar.markdown("**How to refresh data:**")
st.sidebar.code("python src/ingest_prices.py\npython src/build_metrics.py")

# ── Main content ──────────────────────────────────────────────────────────────
st.title("📈 Market Performance & Risk Dashboard")

if not data_loaded:
    st.error(f"⚠️ Could not load data: {error_msg}")
    st.info("Run these commands first:\n```\npython src/ingest_prices.py\npython src/build_metrics.py\n```")
    st.stop()

if returns_df.empty:
    st.warning("No data found. Run the ingestion and metrics scripts first.")
    st.stop()

# ── Tab layout ────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Executive Summary", "⚠️ Risk Monitor", "📉 Price History"])

# =============================================================================
# TAB 1 — Executive Summary
# =============================================================================
with tab1:
    st.subheader("Performance Snapshot")

    if filtered.empty:
        st.warning("No data for selected filters.")
    else:
        # Latest metrics per ticker
        latest = (
            filtered.sort_values("date")
            .groupby("ticker")
            .last()
            .reset_index()
        )

        # KPI cards — show for up to 5 tickers
        cols = st.columns(min(len(latest), 5))
        for i, row in latest.head(5).iterrows():
            with cols[i % 5]:
                ret_1d = row.get("return_1d", 0) or 0
                color  = "🟢" if ret_1d >= 0 else "🔴"
                st.metric(
                    label=row["ticker"],
                    value=f"{ret_1d * 100:.2f}%",
                    delta=f"1D return",
                )

        st.divider()

        # Cumulative return chart
        st.subheader("Cumulative Return vs. SPY")
        fig = px.line(
            filtered,
            x="date",
            y="cumulative_return",
            color="ticker",
            labels={"cumulative_return": "Cumulative Return", "date": "Date"},
            title="Cumulative Return from Start of Period",
        )
        fig.update_yaxes(tickformat=".0%")
        fig.update_layout(hovermode="x unified", legend_title="Ticker")
        st.plotly_chart(fig, use_container_width=True)

        # Summary table
        st.subheader("Return Summary Table")
        summary = latest[["ticker", "return_1d", "return_5d", "return_1m", "cumulative_return"]].copy()
        for col in ["return_1d", "return_5d", "return_1m", "cumulative_return"]:
            summary[col] = summary[col].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "N/A")
        summary.columns = ["Ticker", "1D Return", "5D Return", "1M Return", "Cumulative"]
        st.dataframe(summary.set_index("Ticker"), use_container_width=True)


# =============================================================================
# TAB 2 — Risk Monitor
# =============================================================================
with tab2:
    st.subheader("Risk Metrics")

    if filtered.empty:
        st.warning("No data for selected filters.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            # Rolling volatility
            st.markdown("**Rolling 20-Day Volatility (Annualized)**")
            fig_vol = px.line(
                filtered,
                x="date",
                y="rolling_vol_20d",
                color="ticker",
                labels={"rolling_vol_20d": "Volatility", "date": "Date"},
            )
            fig_vol.update_yaxes(tickformat=".0%")
            fig_vol.update_layout(hovermode="x unified", showlegend=True)
            st.plotly_chart(fig_vol, use_container_width=True)

        with col2:
            # Drawdown
            st.markdown("**Drawdown from Rolling Peak**")
            fig_dd = px.area(
                filtered,
                x="date",
                y="drawdown",
                color="ticker",
                labels={"drawdown": "Drawdown", "date": "Date"},
            )
            fig_dd.update_yaxes(tickformat=".0%")
            fig_dd.update_layout(hovermode="x unified", showlegend=True)
            st.plotly_chart(fig_dd, use_container_width=True)

        # Beta table
        st.subheader(f"Rolling 60-Day Beta vs. {config.BENCHMARK}")
        latest_beta = (
            filtered.sort_values("date")
            .groupby("ticker")[["ticker", "date", "rolling_beta_60d"]]
            .last()
            .reset_index(drop=True)
        )
        latest_beta["rolling_beta_60d"] = latest_beta["rolling_beta_60d"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
        )
        latest_beta.columns = ["Ticker", "As Of Date", "Beta vs SPY"]
        st.dataframe(latest_beta.set_index("Ticker"), use_container_width=True)
        st.caption("Beta > 1 means the stock tends to move more than the market. Beta < 1 means less.")


# =============================================================================
# TAB 3 — Price History
# =============================================================================
with tab3:
    st.subheader("Adjusted Close Price History")

    price_filtered = prices_df[
        prices_df["ticker"].isin(selected_tickers) &
        (prices_df["date"].dt.date >= start_date) &
        (prices_df["date"].dt.date <= end_date)
    ]

    if price_filtered.empty:
        st.warning("No price data for selected filters.")
    else:
        fig_price = px.line(
            price_filtered,
            x="date",
            y="adj_close",
            color="ticker",
            labels={"adj_close": "Adjusted Close ($)", "date": "Date"},
            title="Adjusted Close Prices",
        )
        fig_price.update_layout(hovermode="x unified")
        st.plotly_chart(fig_price, use_container_width=True)

        # Volume chart
        st.subheader("Daily Volume")
        fig_vol2 = px.bar(
            price_filtered,
            x="date",
            y="volume",
            color="ticker",
            barmode="group",
            labels={"volume": "Volume", "date": "Date"},
        )
        st.plotly_chart(fig_vol2, use_container_width=True)
