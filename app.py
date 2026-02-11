import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import timedelta

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="CNG Intelligence Dashboard", layout="wide")

# --------------------------------------------------
# MONTHLY SHEETS
# --------------------------------------------------
MONTHLY_SHEETS = {
    "January 2026": "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM",
    "February 2026": "1bZBzVx1oJUXf4tBIpgJwJan8iwh7alz9CO9Z_5TMB3I"
}

# --------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------
st.sidebar.title("📊 Navigation")
page = st.sidebar.radio(
    "Select View",
    ["Monthly Intelligence Dashboard"]
)

# --------------------------------------------------
# LOAD + CLEAN FUNCTION (BASED ON YOUR WORKING CODE)
# --------------------------------------------------
def load_monthly_data(sheet_id):

    CSV_URL = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    raw = pd.read_csv(CSV_URL, header=2)

    raw.columns = raw.iloc[0]
    df = raw.iloc[1:].copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace("\n", " ")
    )

    # Make unique column names
    def make_unique(cols):
        seen = {}
        new_cols = []
        for col in cols:
            if col not in seen:
                seen[col] = 0
                new_cols.append(col)
            else:
                seen[col] += 1
                new_cols.append(f"{col}_{seen[col]}")
        return new_cols

    df.columns = make_unique(df.columns)

    # Keep only shifts
    df["SHIFT"] = df["SHIFT"].astype(str).str.strip()
    df = df[df["SHIFT"].isin(["A", "B", "C"])]

    # Fix date
    df["DATE"] = df["DATE"].ffill()
    df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["DATE"])

    # Clean numeric
    for col in df.columns:
        if col not in ["DATE", "SHIFT"]:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", "", regex=False)
                .replace("nan", "0")
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Aggregate per day
    daily = df.groupby("DATE", as_index=False).sum(numeric_only=True)

    return daily

# --------------------------------------------------
# FORECAST FUNCTION (NO SKLEARN)
# --------------------------------------------------
def forecast_next_7_days(df, column):
    df = df.sort_values("DATE")
    df["DAY_NUM"] = (df["DATE"] - df["DATE"].min()).dt.days

    X = df["DAY_NUM"].values
    y = df[column].values

    if len(X) < 2:
        return None

    slope, intercept = np.polyfit(X, y, 1)

    last_day = df["DAY_NUM"].max()
    future_days = np.array([last_day + i for i in range(1, 8)])
    future_values = slope * future_days + intercept

    future_dates = [df["DATE"].max() + timedelta(days=i) for i in range(1, 8)]

    return pd.DataFrame({
        "DATE": future_dates,
        "FORECAST": future_values
    })

# --------------------------------------------------
# ALERT SYSTEM
# --------------------------------------------------
def detect_short_alerts(df):
    if "SHORT AMOUNT" not in df.columns:
        return None

    mean = df["SHORT AMOUNT"].mean()
    std = df["SHORT AMOUNT"].std()

    abnormal = df[df["SHORT AMOUNT"] > mean + 2*std]

    return abnormal

# --------------------------------------------------
# MAIN DASHBOARD
# --------------------------------------------------
if page == "Monthly Intelligence Dashboard":

    st.title("🚀 CNG Monthly Intelligence Dashboard")

    selected_month = st.selectbox(
        "Select Month",
        list(MONTHLY_SHEETS.keys())
    )

    daily = load_monthly_data(MONTHLY_SHEETS[selected_month])

    # Sidebar Date Filter
    st.sidebar.header("🔎 Filters")
    date_range = st.sidebar.date_input(
        "Select Date Range",
        [daily["DATE"].min(), daily["DATE"].max()]
    )

    daily = daily[
        (daily["DATE"] >= pd.to_datetime(date_range[0])) &
        (daily["DATE"] <= pd.to_datetime(date_range[1]))
    ]

    def safe(col):
        return daily[col].sum() if col in daily.columns else 0

    # --------------------------------------------------
    # KPIs
    # --------------------------------------------------
    st.subheader("📊 Key Performance Indicators")

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    total_gas = safe("TOTAL DSR QTY. KG")
    credit = safe("CREDIT SALE (RS.)")
    paytm = safe("PAYTM")
    cash = safe("CASH DEPOSIIT IN BANK")
    expenses = safe("EXPENSES")
    short_amt = safe("SHORT AMOUNT")

    estimated_profit = cash + paytm + credit - expenses - short_amt

    k1.metric("🔥 Total Gas Sold (KG)", f"{total_gas:,.0f}")
    k2.metric("💳 Credit Sales (₹)", f"{credit:,.0f}")
    k3.metric("💰 Digital Sales (₹)", f"{paytm:,.0f}")
    k4.metric("🏦 Cash Deposited (₹)", f"{cash:,.0f}")
    k5.metric("💸 Expenses (₹)", f"{expenses:,.0f}")
    k6.metric("📈 Estimated Profit (₹)", f"{estimated_profit:,.0f}")

    st.divider()

    # --------------------------------------------------
    # SALES TREND
    # --------------------------------------------------
    if "TOTAL DSR QTY. KG" in daily.columns:
        fig_qty = px.line(
            daily,
            x="DATE",
            y="TOTAL DSR QTY. KG",
            markers=True,
            title="Daily Gas Sales Trend"
        )
        st.plotly_chart(fig_qty, use_container_width=True)

    # --------------------------------------------------
    # FORECAST
    # --------------------------------------------------
    st.subheader("🔮 7-Day Forecast (Gas Sales)")

    forecast_df = forecast_next_7_days(daily, "TOTAL DSR QTY. KG")

    if forecast_df is not None:
        fig_forecast = px.line(daily, x="DATE", y="TOTAL DSR QTY. KG")
        fig_forecast.add_scatter(
            x=forecast_df["DATE"],
            y=forecast_df["FORECAST"],
            mode="lines",
            name="Forecast"
        )
        st.plotly_chart(fig_forecast, use_container_width=True)

    # --------------------------------------------------
    # ALERTS
    # --------------------------------------------------
    st.subheader("🚨 Risk Alerts")

    abnormal = detect_short_alerts(daily)

    if abnormal is not None and not abnormal.empty:
        st.error(f"⚠️ Abnormal Short Amount detected on {len(abnormal)} days")
        st.dataframe(abnormal[["DATE", "SHORT AMOUNT"]])
    else:
        st.success("No abnormal short amounts detected.")

    # --------------------------------------------------
    # RAW DATA
    # --------------------------------------------------
    st.subheader("📄 Cleaned Daily Aggregated Data")
    st.dataframe(daily, use_container_width=True)
