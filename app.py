import streamlit as st
import pandas as pd
import plotly.express as px

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(page_title="CNG Daily Dashboard", layout="wide")
st.title("📊 CNG Station Daily Operations Dashboard")

# ==================================================
# LOAD DATA
# ==================================================
SHEET_ID = "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
raw = pd.read_csv(CSV_URL, header=2)

# ==================================================
# HEADER FIX
# ==================================================
raw.columns = raw.iloc[0]
df = raw.iloc[1:].copy()

# ==================================================
# CLEAN COLUMNS
# ==================================================
df.columns = (
    df.columns.astype(str)
    .str.strip()
    .str.upper()
    .str.replace("\n", " ")
)

def make_unique(cols):
    seen = {}
    out = []
    for c in cols:
        if c not in seen:
            seen[c] = 0
            out.append(c)
        else:
            seen[c] += 1
            out.append(f"{c}_{seen[c]}")
    return out

df.columns = make_unique(df.columns)

# ==================================================
# SHIFT + DATE CLEANING
# ==================================================
df["SHIFT"] = df["SHIFT"].astype(str).str.strip()
df = df[df["SHIFT"].isin(["A", "B", "C"])]

df["DATE"] = df["DATE"].ffill()
df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
df = df.dropna(subset=["DATE"])

# ==================================================
# NUMERIC CLEANING
# ==================================================
for c in df.columns:
    if c not in ["DATE", "SHIFT"]:
        df[c] = (
            df[c].astype(str)
            .str.replace(",", "", regex=False)
            .replace("nan", "0")
        )
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

# ==================================================
# SIDEBAR FILTER (RAW DATA LEVEL)
# ==================================================
st.sidebar.header("🔎 Filters")

min_date = df["DATE"].min()
max_date = df["DATE"].max()

date_range = st.sidebar.date_input(
    "Select Date Range",
    [min_date, max_date]
)

# 🔥 FILTER RAW DATA FIRST
df_filtered = df[
    (df["DATE"] >= pd.to_datetime(date_range[0])) &
    (df["DATE"] <= pd.to_datetime(date_range[1]))
]

# ==================================================
# DAILY AGGREGATION (FILTERED)
# ==================================================
daily = df_filtered.groupby("DATE", as_index=False).sum(numeric_only=True)

def safe(col):
    return daily[col].sum() if col in daily.columns else 0

# ==================================================
# TARGET
# ==================================================
st.sidebar.divider()
target = st.sidebar.number_input("Daily Target (KG)", min_value=0, value=1000)

actual = safe("TOTAL DSR QTY. KG")
achievement = (actual / target * 100) if target > 0 else 0

st.sidebar.metric(
    "Target Achievement",
    f"{achievement:.1f}%",
    f"{actual - target:.0f} KG"
)

# ==================================================
# KPI CARDS
# ==================================================
k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("🔥 Gas Sold (KG)", f"{safe('TOTAL DSR QTY. KG'):,.0f}")
k2.metric("💳 Credit (₹)", f"{safe('CREDIT SALE (RS.)'):,.0f}")
k3.metric("💰 Paytm (₹)", f"{safe('PAYTM'):,.0f}")
k4.metric("🏦 Bank Deposit (₹)", f"{safe('CASH DEPOSIIT IN BANK'):,.0f}")
k5.metric("💸 Expenses (₹)", f"{safe('EXPENSES'):,.0f}")
k6.metric("⚠️ Short (₹)", f"{safe('SHORT AMOUNT'):,.0f}")

st.divider()

# ==================================================
# TABS
# ==================================================
tabs = st.tabs([
    "📈 Daily Overview",
    "🔄 Shift Analysis",
    "📅 Monthly Summary",
    "🚨 Alerts",
    "📄 Data"
])

# ==================================================
# DAILY OVERVIEW
# ==================================================
with tabs[0]:
    fig = px.line(
        daily,
        x="DATE",
        y="TOTAL DSR QTY. KG",
        markers=True,
        title="Daily Gas Sales (KG)"
    )
    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# ✅ FIXED SHIFT ANALYSIS
# ==================================================
with tabs[1]:
    # DAILY + SHIFT (FILTERED)
    shift_daily = (
        df_filtered
        .groupby(["DATE", "SHIFT"], as_index=False)
        .sum(numeric_only=True)
    )

    fig_shift = px.bar(
        shift_daily,
        x="DATE",
        y="TOTAL DSR QTY. KG",
        color="SHIFT",
        barmode="group",
        title="Gas Sales by Shift (A / B / C)"
    )
    st.plotly_chart(fig_shift, use_container_width=True)

    # TOTAL BY SHIFT
    shift_total = (
        df_filtered
        .groupby("SHIFT", as_index=False)
        .sum(numeric_only=True)
    )

    fig_shift_total = px.pie(
        shift_total,
        names="SHIFT",
        values="TOTAL DSR QTY. KG",
        title="Total Contribution by Shift"
    )
    st.plotly_chart(fig_shift_total, use_container_width=True)

# ==================================================
# MONTHLY SUMMARY
# ==================================================
with tabs[2]:
    daily["MONTH"] = daily["DATE"].dt.to_period("M").astype(str)
    monthly = daily.groupby("MONTH", as_index=False).sum(numeric_only=True)
    st.dataframe(monthly, use_container_width=True)

# ==================================================
# ALERTS
# ==================================================
with tabs[3]:
    if safe("SHORT AMOUNT") > 0:
        st.error(f"🚨 Short Amount: ₹{safe('SHORT AMOUNT'):,.0f}")
    else:
        st.success("✅ No Short Amount")

# ==================================================
# DATA VIEW
# ==================================================
with tabs[4]:
    st.dataframe(df_filtered, use_container_width=True)
