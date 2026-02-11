import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(
    page_title="Fuel Station Analytics Suite",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================
# CONSTANTS
# ======================================================
DAILY_MASTER_SHEET = "1_NDdrYnUJnFoJHwc5dZUy5bM920UqMmxP2dUJErGtNA"

MONTHLY_SHEETS = {
    "January 2026": "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM",
    "February 2026": "1bZBzVx1oJUXf4tBIpgJwJan8iwh7alz9CO9Z_5TMB3I"
}

# ======================================================
# SESSION STATE
# ======================================================
if "daily_gid_map" not in st.session_state:
    st.session_state.daily_gid_map = {}

# ======================================================
# UTILITIES
# ======================================================
@st.cache_data
def load_daily_sheet(gid):
    url = f"https://docs.google.com/spreadsheets/d/{DAILY_MASTER_SHEET}/export?format=csv&gid={gid}"
    return pd.read_csv(url, header=None)

@st.cache_data
def load_monthly_sheet(sheet_id):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    return pd.read_csv(url, header=None)

def safe(df, r, c):
    try:
        return df.iloc[r, c]
    except:
        return None

def header(title):
    st.markdown(f"<h2 style='color:#2E4053'>{title}</h2>", unsafe_allow_html=True)

# ======================================================
# SIDEBAR NAVIGATION
# ======================================================
st.sidebar.title("⛽ Fuel Station Suite")

page = st.sidebar.radio(
    "Navigate",
    ["📅 Add Daily GID",
     "📊 Daily Dashboard",
     "📈 Monthly Intelligence"]
)

# ======================================================
# PAGE 1 — ADD DAILY GID
# ======================================================
if page == "📅 Add Daily GID":

    header("Add Daily Sheet GID")

    selected_date = st.date_input("Select Date", value=datetime.today())
    gid = st.text_input("Enter GID")

    if st.button("Save"):
        formatted = selected_date.strftime("%d.%m.%y")
        st.session_state.daily_gid_map[formatted] = gid
        st.success(f"Saved for {formatted}")

    st.write("### Saved GIDs")
    st.json(st.session_state.daily_gid_map)

# ======================================================
# PAGE 2 — DAILY DASHBOARD
# ======================================================
elif page == "📊 Daily Dashboard":

    header("Daily Performance Dashboard")

    if not st.session_state.daily_gid_map:
        st.warning("Add at least one GID first.")
        st.stop()

    selected_date = st.selectbox(
        "Select Date",
        list(st.session_state.daily_gid_map.keys())
    )

    df = load_daily_sheet(st.session_state.daily_gid_map[selected_date])

    # Extract Consolidated Section
    shift_df = pd.DataFrame({
        "Shift": ["A", "B", "C"],
        "QTY": [safe(df,7,1), safe(df,9,1), safe(df,11,1)],
        "SALE": [safe(df,7,2), safe(df,9,2), safe(df,11,2)],
        "CASH": [safe(df,7,3), safe(df,9,3), safe(df,11,3)],
        "PAYTM": [safe(df,7,4), safe(df,9,4), safe(df,11,4)],
        "CREDIT": [safe(df,7,6), safe(df,9,6), safe(df,11,6)],
        "DIFF": [safe(df,7,8), safe(df,9,8), safe(df,11,8)],
    })

    total_sale = safe(df,13,2)
    total_diff = safe(df,13,8)

    k1,k2,k3 = st.columns(3)
    k1.metric("Total Sale ₹", total_sale)
    k2.metric("Total Difference ₹", total_diff)
    k3.metric("Total Quantity", safe(df,13,1))

    st.dataframe(shift_df, use_container_width=True)

    fig = px.bar(shift_df, x="Shift", y="SALE", title="Shift Sales")
    st.plotly_chart(fig, use_container_width=True)

# ======================================================
# PAGE 3 — MONTHLY INTELLIGENCE
# ======================================================
elif page == "📈 Monthly Intelligence":

    header("Monthly Intelligence Engine")

    selected_month = st.selectbox("Select Month", list(MONTHLY_SHEETS.keys()))
    raw = load_monthly_sheet(MONTHLY_SHEETS[selected_month]).fillna("")

    parsed = []

    for i in range(len(raw)):
        if str(raw.iloc[i,0]).strip().upper() == "TOTAL":
            try:
                parsed.append({
                    "Day": len(parsed)+1,
                    "QTY": float(raw.iloc[i,1]),
                    "SALE": float(raw.iloc[i,2]),
                    "CASH": float(raw.iloc[i,3]),
                    "PAYTM": float(raw.iloc[i,4]),
                    "ATM": float(raw.iloc[i,5]),
                    "CREDIT": float(raw.iloc[i,6]),
                    "COLLECTION": float(raw.iloc[i,7]),
                    "DIFF": float(raw.iloc[i,8])
                })
            except:
                pass

    if not parsed:
        st.error("Could not parse monthly structure.")
        st.stop()

    monthly_df = pd.DataFrame(parsed)

    # ======================================================
    # KPIs
    # ======================================================
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Monthly Sale ₹", round(monthly_df["SALE"].sum(),2))
    k2.metric("Avg Daily Sale ₹", round(monthly_df["SALE"].mean(),2))
    k3.metric("Highest Day ₹", round(monthly_df["SALE"].max(),2))
    k4.metric("Total Diff ₹", round(monthly_df["DIFF"].sum(),2))

    st.divider()

    # ======================================================
    # 7-DAY FORECAST
    # ======================================================
    st.subheader("📊 7-Day Sales Forecast")

    X = np.array(monthly_df.index).reshape(-1,1)
    y = monthly_df["SALE"].values

    model = LinearRegression()
    model.fit(X,y)

    future_days = np.array(range(len(monthly_df), len(monthly_df)+7)).reshape(-1,1)
    forecast = model.predict(future_days)

    forecast_df = pd.DataFrame({
        "Future Day": range(len(monthly_df)+1, len(monthly_df)+8),
        "Forecasted Sale": forecast
    })

    fig_forecast = go.Figure()
    fig_forecast.add_trace(go.Scatter(
        x=monthly_df["Day"],
        y=monthly_df["SALE"],
        mode='lines+markers',
        name='Actual'
    ))
    fig_forecast.add_trace(go.Scatter(
        x=forecast_df["Future Day"],
        y=forecast_df["Forecasted Sale"],
        mode='lines+markers',
        name='Forecast'
    ))
    st.plotly_chart(fig_forecast, use_container_width=True)

    # ======================================================
    # ALERT SYSTEM
    # ======================================================
    st.subheader("🚨 Short / Excess Alert System")

    threshold = monthly_df["DIFF"].std() * 2
    alerts = monthly_df[abs(monthly_df["DIFF"]) > threshold]

    if not alerts.empty:
        st.error("Abnormal Short/Excess Detected")
        st.dataframe(alerts)
    else:
        st.success("No abnormal short/excess detected")

    # ======================================================
    # PROFIT ESTIMATION MODULE
    # ======================================================
    st.subheader("💰 Profit Estimation")

    profit_margin = st.slider("Estimated Profit per Unit (₹)", 0.0, 10.0, 2.0)

    monthly_df["Estimated Profit"] = monthly_df["QTY"] * profit_margin

    st.metric("Estimated Monthly Profit ₹",
              round(monthly_df["Estimated Profit"].sum(),2))

    fig_profit = px.bar(monthly_df,
                        x="Day",
                        y="Estimated Profit",
                        title="Daily Estimated Profit")

    st.plotly_chart(fig_profit, use_container_width=True)

    # ======================================================
    # Correlation
    # ======================================================
    st.subheader("📈 Correlation Matrix")

    corr = monthly_df.corr()
    fig_corr = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.columns
        )
    )
    st.plotly_chart(fig_corr, use_container_width=True)
