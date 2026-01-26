import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="CNG Daily Dashboard", layout="wide")
st.title("📊 CNG Station Daily Operations Dashboard")

# --------------------------------------------------
# LOAD DATA FROM GOOGLE SHEETS
# --------------------------------------------------
SHEET_ID = "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

raw = pd.read_csv(CSV_URL, header=2)

# --------------------------------------------------
# FIX HEADERS
# --------------------------------------------------
raw.columns = raw.iloc[0]
df = raw[1:].copy()

df.columns = (
    df.columns.astype(str)
    .str.strip()
    .str.upper()
    .str.replace("\n", " ")
)

# --------------------------------------------------
# KEEP ONLY RELEVANT ROWS (SHIFTS)
# --------------------------------------------------
df["SHIFT"] = df["SHIFT"].str.strip()
df = df[df["SHIFT"].isin(["A", "B", "C"])]

# --------------------------------------------------
# FIX DATE COLUMN (FORWARD FILL)
# --------------------------------------------------
df["DATE"] = df["DATE"].ffill()
df["DATE"] = pd.to_datetime(df["DATE"], format="%d.%m.%y")

# --------------------------------------------------
# CLEAN NUMERIC COLUMNS
# --------------------------------------------------
numeric_cols = [
    "DSR (QTY.) KG.",
    "TOTAL DSR QTY. KG",
    "LCV (QTY.) KG",
    "CREDIT SALE (QTY.) KG",
    "CREDIT SALE (RS.)",
    "TOTAL AMOUNT RTGS PAID",
    "ATM",
    "PAYTM",
    "CASH DEPOSIIT IN BANK",
    "SHORT AMOUNT",
    "EXPENSES",
    "FILLING BOY"
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .replace("nan", "0")
            .astype(float)
        )

# --------------------------------------------------
# AGGREGATE PER DAY
# --------------------------------------------------
daily = df.groupby("DATE", as_index=False).sum()

# --------------------------------------------------
# SIDEBAR FILTER
# --------------------------------------------------
st.sidebar.header("🔎 Filters")

date_range = st.sidebar.date_input(
    "Select Date Range",
    [daily["DATE"].min(), daily["DATE"].max()]
)

daily = daily[
    (daily["DATE"] >= pd.to_datetime(date_range[0])) &
    (daily["DATE"] <= pd.to_datetime(date_range[1]))
]

# --------------------------------------------------
# KPIs
# --------------------------------------------------
k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("🔥 Total Gas Sold (KG)", f"{daily['TOTAL DSR QTY. KG'].sum():,.0f}")
k2.metric("💰 Credit Sales (₹)", f"{daily['CREDIT SALE (RS.)'].sum():,.0f}")
k3.metric("💳 Paytm (₹)", f"{daily['PAYTM'].sum():,.0f}")
k4.metric("🏦 Cash Deposited (₹)", f"{daily['CASH DEPOSIIT IN BANK'].sum():,.0f}")
k5.metric("💸 Expenses (₹)", f"{daily['EXPENSES'].sum():,.0f}")
k6.metric("⚠️ Short Amount (₹)", f"{daily['SHORT AMOUNT'].sum():,.0f}")

st.divider()

# --------------------------------------------------
# DAILY SALES TREND
# --------------------------------------------------
fig_qty = px.line(
    daily,
    x="DATE",
    y="TOTAL DSR QTY. KG",
    markers=True,
    title="Daily Gas Sales (KG)"
)
st.plotly_chart(fig_qty, use_container_width=True)

# --------------------------------------------------
# PAYMENT MODE BREAKDOWN
# --------------------------------------------------
payment_df = pd.DataFrame({
    "Mode": ["ATM", "Paytm", "Cash Deposit"],
    "Amount": [
        daily["ATM"].sum(),
        daily["PAYTM"].sum(),
        daily["CASH DEPOSIIT IN BANK"].sum()
    ]
})

fig_pay = px.pie(payment_df, names="Mode", values="Amount", title="Payment Mode Split")
st.plotly_chart(fig_pay, use_container_width=True)

# --------------------------------------------------
# CASH RECONCILIATION
# --------------------------------------------------
cash_df = pd.DataFrame({
    "Type": ["Cash Deposit", "Expenses", "Short Amount"],
    "Amount": [
        daily["CASH DEPOSIIT IN BANK"].sum(),
        daily["EXPENSES"].sum(),
        daily["SHORT AMOUNT"].sum()
    ]
})

fig_cash = px.bar(cash_df, x="Type", y="Amount", title="Cash Reconciliation")
st.plotly_chart(fig_cash, use_container_width=True)

# --------------------------------------------------
# RAW DATA
# --------------------------------------------------
st.subheader("📄 Daily Aggregated Data")
st.dataframe(daily, use_container_width=True)
