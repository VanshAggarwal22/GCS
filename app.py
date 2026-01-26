import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="CNG Daily Dashboard", layout="wide")
st.title("📊 CNG Station Daily Operations Dashboard")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
SHEET_ID = "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

raw = pd.read_csv(CSV_URL, header=2)

# --------------------------------------------------
# FIX HEADER ROW
# --------------------------------------------------
raw.columns = raw.iloc[0]
df = raw.iloc[1:].copy()

# --------------------------------------------------
# CLEAN COLUMN NAMES
# --------------------------------------------------
df.columns = (
    df.columns.astype(str)
    .str.strip()
    .str.upper()
    .str.replace("\n", " ")
)

# --------------------------------------------------
# MAKE COLUMN NAMES UNIQUE (🔥 CRITICAL FIX)
# --------------------------------------------------
df.columns = pd.io.parsers.ParserBase({'names': df.columns})._maybe_dedup_names(df.columns)

# --------------------------------------------------
# KEEP ONLY SHIFT ROWS
# --------------------------------------------------
df["SHIFT"] = df["SHIFT"].astype(str).str.strip()
df = df[df["SHIFT"].isin(["A", "B", "C"])]

# --------------------------------------------------
# FIX DATE (FORWARD FILL FIRST!)
# --------------------------------------------------
df["DATE"] = df["DATE"].ffill()
df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
df = df.dropna(subset=["DATE"])

# --------------------------------------------------
# CLEAN NUMERIC COLUMNS
# --------------------------------------------------
for col in df.columns:
    if col not in ["DATE", "SHIFT"]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("nan", "0")
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# --------------------------------------------------
# AGGREGATE PER DAY (THIS FIXES MISSING DATES)
# --------------------------------------------------
daily = df.groupby("DATE", as_index=False).sum(numeric_only=True)

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
# KPI MAPPING (SAFE)
# --------------------------------------------------
def safe(col):
    return daily[col].sum() if col in daily.columns else 0

# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------
k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("🔥 Total Gas Sold (KG)", f"{safe('TOTAL DSR QTY. KG'):,.0f}")
k2.metric("💳 Credit Sales (₹)", f"{safe('CREDIT SALE (RS.)'):,.0f}")
k3.metric("💰 Paytm (₹)", f"{safe('PAYTM'):,.0f}")
k4.metric("🏦 Cash Deposited (₹)", f"{safe('CASH DEPOSIIT IN BANK'):,.0f}")
k5.metric("💸 Expenses (₹)", f"{safe('EXPENSES'):,.0f}")
k6.metric("⚠️ Short Amount (₹)", f"{safe('SHORT AMOUNT'):,.0f}")

st.divider()

# --------------------------------------------------
# DAILY SALES TREND (NO DUPLICATES NOW)
# --------------------------------------------------
if "TOTAL DSR QTY. KG" in daily.columns:
    fig_qty = px.line(
        daily,
        x="DATE",
        y="TOTAL DSR QTY. KG",
        markers=True,
        title="Daily Gas Sales (KG)"
    )
    st.plotly_chart(fig_qty, use_container_width=True)

# --------------------------------------------------
# PAYMENT MODE SPLIT
# --------------------------------------------------
payment_df = pd.DataFrame({
    "Mode": ["ATM", "Paytm", "Cash Deposit"],
    "Amount": [
        safe("ATM"),
        safe("PAYTM"),
        safe("CASH DEPOSIIT IN BANK")
    ]
})

payment_df = payment_df[payment_df["Amount"] > 0]

fig_pay = px.pie(payment_df, names="Mode", values="Amount", title="Payment Mode Split")
st.plotly_chart(fig_pay, use_container_width=True)

# --------------------------------------------------
# CASH RECONCILIATION
# --------------------------------------------------
cash_df = pd.DataFrame({
    "Type": ["Cash Deposit", "Expenses", "Short Amount"],
    "Amount": [
        safe("CASH DEPOSIIT IN BANK"),
        safe("EXPENSES"),
        safe("SHORT AMOUNT")
    ]
})

fig_cash = px.bar(cash_df, x="Type", y="Amount", title="Cash Reconciliation")
st.plotly_chart(fig_cash, use_container_width=True)

# --------------------------------------------------
# RAW DATA
# --------------------------------------------------
st.subheader("📄 Cleaned Daily Data")
st.dataframe(daily, use_container_width=True)
