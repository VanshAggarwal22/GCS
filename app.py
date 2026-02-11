import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Operations Intelligence Dashboard", layout="wide")

# ================= CONFIG =================

MONTHLY_SHEETS = {
    "January 2026": "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM",
    "February 2026": "1bZBzVx1oJUXf4tBIpgJwJan8iwh7alz9CO9Z_5TMB3I"
}

if "daily_map" not in st.session_state:
    st.session_state.daily_map = {}

# ================= LOAD GOOGLE SHEET =================

def load_google_sheet(sheet_id, gid="0"):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Fetch failed: {e}")
        return None

# ================= PARSER =================

def parse_structure(df):

    if df is None:
        return None

    df = df.dropna(how="all")

    # Detect date column
    date_col = None
    for col in df.columns:
        if "date" in str(col).lower():
            date_col = col
            break

    if date_col is None:
        return None

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])

    df = df.rename(columns={date_col: "Date"})

    for col in df.columns:
        if col != "Date":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.fillna(0)
    return df

# ================= FORECAST =================

def forecast_next_7_days(df, column):

    df = df.sort_values("Date")
    df["Day"] = (df["Date"] - df["Date"].min()).dt.days

    X = df["Day"].values
    y = df[column].values

    if len(X) < 2:
        return None

    slope, intercept = np.polyfit(X, y, 1)

    last_day = df["Day"].max()

    future_days = np.arange(last_day + 1, last_day + 8)
    future_vals = slope * future_days + intercept

    future_dates = [df["Date"].max() + timedelta(days=i) for i in range(1, 8)]

    return pd.DataFrame({"Date": future_dates, "Forecast": future_vals})

# ================= ALERT =================

def generate_alerts(df):

    alerts = []

    for col in df.columns:
        if "short" in col.lower() or "excess" in col.lower():

            mean = df[col].mean()
            std = df[col].std()

            abnormal = df[df[col] > mean + 2 * std]

            if not abnormal.empty:
                alerts.append(f"Abnormal {col} detected")

    return alerts

# ================= PROFIT =================

def estimate_profit(df):

    sales = None
    purchase = None

    for col in df.columns:
        if "sale" in col.lower():
            sales = col
        if "purchase" in col.lower() or "cost" in col.lower():
            purchase = col

    if sales and purchase:
        return (df[sales] - df[purchase]).sum()

    return None

# ================= SIDEBAR =================

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Page",
    ["Daily GID Entry", "Daily Dashboard", "Monthly Dashboard"]
)

# =====================================================
# PAGE 1 DAILY ENTRY
# =====================================================

if page == "Daily GID Entry":

    st.title("Daily Mapping Entry")

    date = st.date_input("Select Date")

    month = st.selectbox("Select Month Sheet", list(MONTHLY_SHEETS.keys()))
    gid = st.text_input("Enter GID")

    if st.button("Save Mapping"):

        st.session_state.daily_map[str(date)] = {
            "sheet_id": MONTHLY_SHEETS[month],
            "gid": gid
        }

        st.success("Saved!")

    st.write(st.session_state.daily_map)

# =====================================================
# PAGE 2 DAILY DASHBOARD
# =====================================================

if page == "Daily Dashboard":

    st.title("Daily Dashboard")

    if not st.session_state.daily_map:
        st.warning("No mapping added yet")

    else:

        selected_date = st.selectbox(
            "Select Date",
            list(st.session_state.daily_map.keys())
        )

        mapping = st.session_state.daily_map[selected_date]

        raw = load_google_sheet(mapping["sheet_id"], mapping["gid"])
        df = parse_structure(raw)

        if df is None:
            st.error("Parsing failed")
        else:

            st.dataframe(df)

            numeric = df.select_dtypes(include=np.number).columns

            col1, col2, col3 = st.columns(3)

            if len(numeric) > 0:
                col1.metric("Total", int(df[numeric[0]].sum()))

            if len(numeric) > 1:
                col2.metric("Average", round(df[numeric[1]].mean(), 2))

            profit = estimate_profit(df)
            if profit:
                col3.metric("Profit", round(profit, 2))

# =====================================================
# PAGE 3 MONTHLY DASHBOARD
# =====================================================

if page == "Monthly Dashboard":

    st.title("Monthly Intelligence Dashboard")

    month = st.selectbox("Select Month", list(MONTHLY_SHEETS.keys()))

    sheet_id = MONTHLY_SHEETS[month]

    raw = load_google_sheet(sheet_id)
    df = parse_structure(raw)

    if df is None:
        st.error("Monthly parsing failed")
    else:

        st.dataframe(df)

        numeric = df.select_dtypes(include=np.number).columns

        st.subheader("KPIs")

        kpi = st.columns(4)

        if len(numeric) > 0:
            kpi[0].metric("Total Volume", int(df[numeric[0]].sum()))

        if len(numeric) > 1:
            kpi[1].metric("Average Daily", round(df[numeric[1]].mean(), 2))

        profit = estimate_profit(df)
        if profit:
            kpi[2].metric("Estimated Profit", round(profit, 2))

        kpi[3].metric("Days", len(df))

        st.subheader("Trend")

        for col in numeric[:3]:
            fig = px.line(df, x="Date", y=col)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Forecast")

        if len(numeric) > 0:
            forecast = forecast_next_7_days(df, numeric[0])

            if forecast is not None:

                fig = px.line(df, x="Date", y=numeric[0])
                fig.add_scatter(x=forecast["Date"], y=forecast["Forecast"], mode="lines")

                st.plotly_chart(fig, use_container_width=True)

        st.subheader("Alerts")

        alerts = generate_alerts(df)

        if alerts:
            for a in alerts:
                st.error(a)
        else:
            st.success("No abnormal activity")
