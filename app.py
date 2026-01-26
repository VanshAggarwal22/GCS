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
# CLEAN COLUMN NAMES
# ==================================================
df.columns = (
    df.columns.astype(str)
    .str.strip()
    .str.upper()
    .str.replace("\n", " ")
)

# Make column names unique
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
# IDENTIFY DATE & SHIFT COLUMNS (IMPORTANT FIX)
# ==================================================
date_col = df.columns[0]      # First column = DATE
shift_col = df.columns[1]     # Second column = A / B / C

df.rename(columns={date_col: "DATE", shift_col: "SHIFT"}, inplace=True)

# ==================================================
# DATE & SHIFT CLEANING
# ==================================================
df["SHIFT"] = df["SHIFT"].astype(str).str.strip().str.upper()
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
            df[c]
            .astype(str)
            .str.replace(",", "", regex=False)
            .replace("nan", "0")
        )
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

# ==================================================
# SIDEBAR FILTER (RAW LEVEL)
# ==================================================
st.sidebar.header("🔎 Filters")

date_range = st.sidebar.date_input(
    "Select Date Range",
    [df["DATE"].min(), df["DATE"].max()]
)

df_f = df[
    (df["DATE"] >= pd.to_datetime(date_range[0])) &
    (df["DATE"] <= pd.to_datetime(date_range[1]))
]

# ==================================================
# DAILY AGGREGATION (DO NOT CHANGE)
# ==================================================
daily = df_f.groupby("DATE", as_index=False).sum(numeric_only=True)

def safe(col):
    return daily[col].sum() if col in daily.columns else 0

# ==================================================
# KPI CARDS
# ==================================================
k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("🔥 Gas Sold (KG)", f"{safe('TOTAL DSR QTY. KG'):,.0f}")
k2.metric("💳 Credit Sales (₹)", f"{safe('CREDIT SALE (RS.)'):,.0f}")
k3.metric("💰 Paytm (₹)", f"{safe('PAYTM'):,.0f}")
k4.metric("🏦 Cash Deposit (₹)", f"{safe('CASH DEPOSIIT IN BANK'):,.0f}")
k5.metric("💸 Expenses (₹)", f"{safe('EXPENSES'):,.0f}")
k6.metric("⚠️ Short Amount (₹)", f"{safe('SHORT AMOUNT'):,.0f}")

st.divider()

# ==================================================
# TABS
# ==================================================
tabs = st.tabs([
    "📈 Daily Overview",
    "🔄 Shift Analysis",
    "📅 Monthly Summary",
    "📄 Raw Data"
])

# ==================================================
# TAB 1: DAILY OVERVIEW (UNCHANGED)
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
# TAB 2: ✅ CORRECT SHIFT ANALYSIS
# ==================================================
with tabs[1]:
    shift_daily = (
        df_f
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

    # ------------------------------
    # SHIFT-WISE CASH & PAYMENTS
    # ------------------------------
    cash_cols = [
        c for c in shift_daily.columns
        if any(k in c for k in ["CASH", "PAYTM", "ATM", "RTGS", "PID"])
    ]

    if cash_cols:
        cash_shift = (
            df_f
            .groupby("SHIFT", as_index=False)[cash_cols]
            .sum()
        )

        fig_cash = px.bar(
            cash_shift.melt(id_vars="SHIFT", var_name="Mode", value_name="Amount"),
            x="SHIFT",
            y="Amount",
            color="Mode",
            title="Shift-wise Cash / Digital Collection",
            barmode="stack"
        )
        st.plotly_chart(fig_cash, use_container_width=True)

# ==================================================
# TAB 3: MONTHLY SUMMARY
# ==================================================
with tabs[2]:
    daily["MONTH"] = daily["DATE"].dt.to_period("M").astype(str)
    monthly = daily.groupby("MONTH", as_index=False).sum(numeric_only=True)
    st.dataframe(monthly, use_container_width=True)

# ==================================================
# TAB 4: RAW DATA
# ==================================================
with tabs[3]:
    st.dataframe(df_f, use_container_width=True)
