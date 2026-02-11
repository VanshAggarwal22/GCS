import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Operations Intelligence Dashboard",
                   layout="wide")

# ==============================
# CONFIG
# ==============================

MONTHLY_SHEETS = {
    "January 2026": "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM",
    "February 2026": "1bZBzVx1oJUXf4tBIpgJwJan8iwh7alz9CO9Z_5TMB3I"
}

if "daily_gid_map" not in st.session_state:
    st.session_state.daily_gid_map = {}

# ==============================
# UTIL FUNCTIONS
# ==============================

def load_google_sheet(sheet_id, gid="0"):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)


def parse_structure(df):
    df = df.dropna(how="all")

    # Auto detect date column
    date_col = None
    for col in df.columns:
        if "date" in str(col).lower():
            date_col = col
            break

    if date_col is None:
        df.columns = df.iloc[0]
        df = df[1:]
        for col in df.columns:
            if "date" in str(col).lower():
                date_col = col
                break

    if date_col is None:
        return None

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])

    df = df.rename(columns={date_col: "Date"})

    numeric_cols = []
    for col in df.columns:
        if col != "Date":
            df[col] = pd.to_numeric(df[col], errors="coerce")
            numeric_cols.append(col)

    df = df.fillna(0)
    return df


def forecast_next_7_days(df, target_col):
    df = df.sort_values("Date")
    df["DayNumber"] = (df["Date"] - df["Date"].min()).dt.days

    X = df["DayNumber"].values
    y = df[target_col].values

    if len(X) < 2:
        return None

    slope, intercept = np.polyfit(X, y, 1)

    last_day = df["DayNumber"].max()
    future_days = np.array([last_day + i for i in range(1, 8)])
    future_values = slope * future_days + intercept

    future_dates = [df["Date"].max() + timedelta(days=i) for i in range(1, 8)]

    forecast_df = pd.DataFrame({
        "Date": future_dates,
        "Forecast": future_values
    })

    return forecast_df


def generate_alerts(df):
    alerts = []

    for col in df.columns:
        if "short" in col.lower() or "excess" in col.lower():
            mean = df[col].mean()
            std = df[col].std()

            abnormal = df[df[col] > mean + 2 * std]

            if not abnormal.empty:
                alerts.append(f"⚠️ Abnormal high {col} detected on {len(abnormal)} days.")

    return alerts


def estimate_profit(df):
    sales_col = None
    purchase_col = None

    for col in df.columns:
        if "sale" in col.lower():
            sales_col = col
        if "purchase" in col.lower() or "cost" in col.lower():
            purchase_col = col

    if sales_col and purchase_col:
        df["Estimated Profit"] = df[sales_col] - df[purchase_col]
        return df["Estimated Profit"].sum()

    return None


# ==============================
# SIDEBAR NAVIGATION
# ==============================

st.sidebar.title("📊 Navigation")

page = st.sidebar.radio(
    "Select Page",
    ["Daily GID Entry",
     "Daily Dashboard",
     "Monthly Intelligence Dashboard"]
)

# ==============================
# PAGE 1 – DAILY GID ENTRY
# ==============================

if page == "Daily GID Entry":

    st.title("📅 Daily GID Mapping")

    selected_date = st.date_input("Select Date", datetime.today())
    gid_input = st.text_input("Enter GID for this Date")

    if st.button("Save GID"):
        if gid_input:
            st.session_state.daily_gid_map[str(selected_date)] = gid_input
            st.success("GID saved successfully.")

    st.subheader("Saved Mappings")
    st.write(st.session_state.daily_gid_map)


# ==============================
# PAGE 2 – DAILY DASHBOARD
# ==============================

if page == "Daily Dashboard":

    st.title("📈 Daily Operations Dashboard")

    if not st.session_state.daily_gid_map:
        st.warning("No GIDs saved yet.")
    else:
        selected_date = st.selectbox(
            "Select Date",
            list(st.session_state.daily_gid_map.keys())
        )

        sheet_id = list(MONTHLY_SHEETS.values())[0]  # using first sheet base
        gid = st.session_state.daily_gid_map[selected_date]

        try:
            raw_df = load_google_sheet(sheet_id, gid)
            df = parse_structure(raw_df)

            if df is None:
                st.error("Could not parse daily structure.")
            else:
                st.success("Data Loaded Successfully")

                st.dataframe(df)

                # KPIs
                col1, col2, col3 = st.columns(3)

                numeric_cols = df.select_dtypes(include=np.number).columns

                if len(numeric_cols) >= 1:
                    col1.metric("Total Volume", int(df[numeric_cols[0]].sum()))

                if len(numeric_cols) >= 2:
                    col2.metric("Average Value", round(df[numeric_cols[1]].mean(), 2))

                profit = estimate_profit(df)
                if profit:
                    col3.metric("Estimated Profit", round(profit, 2))

        except:
            st.error("Error fetching daily sheet.")


# ==============================
# PAGE 3 – MONTHLY DASHBOARD
# ==============================

if page == "Monthly Intelligence Dashboard":

    st.title("🚀 Monthly Intelligence Dashboard")

    selected_month = st.selectbox(
        "Select Month",
        list(MONTHLY_SHEETS.keys())
    )

    sheet_id = MONTHLY_SHEETS[selected_month]

    try:
        raw_df = load_google_sheet(sheet_id)
        df = parse_structure(raw_df)

        if df is None:
            st.error("Could not parse monthly structure.")
        else:

            st.success("Monthly Data Loaded")

            st.dataframe(df)

            numeric_cols = df.select_dtypes(include=np.number).columns

            # ================= KPIs =================

            st.subheader("📊 Key Performance Indicators")

            kpi_cols = st.columns(4)

            if len(numeric_cols) >= 1:
                kpi_cols[0].metric("Total Volume",
                                   int(df[numeric_cols[0]].sum()))

            if len(numeric_cols) >= 2:
                kpi_cols[1].metric("Average Daily",
                                   round(df[numeric_cols[1]].mean(), 2))

            profit = estimate_profit(df)
            if profit:
                kpi_cols[2].metric("Estimated Monthly Profit",
                                   round(profit, 2))

            kpi_cols[3].metric("Total Days", len(df))

            # ================= TRENDS =================

            st.subheader("📈 Trend Analysis")

            for col in numeric_cols[:3]:
                fig = px.line(df, x="Date", y=col,
                              title=f"{col} Trend")
                st.plotly_chart(fig, use_container_width=True)

            # ================= FORECAST =================

            st.subheader("🔮 Forecast Next 7 Days")

            if len(numeric_cols) >= 1:
                forecast_df = forecast_next_7_days(df, numeric_cols[0])

                if forecast_df is not None:
                    fig_forecast = px.line(df, x="Date", y=numeric_cols[0])
                    fig_forecast.add_scatter(
                        x=forecast_df["Date"],
                        y=forecast_df["Forecast"],
                        mode="lines",
                        name="Forecast"
                    )
                    st.plotly_chart(fig_forecast,
                                    use_container_width=True)

            # ================= ALERT SYSTEM =================

            st.subheader("🚨 Alerts & Risk Monitoring")

            alerts = generate_alerts(df)

            if alerts:
                for alert in alerts:
                    st.error(alert)
            else:
                st.success("No abnormal short/excess detected.")

    except:
        st.error("Error fetching monthly sheet.")
