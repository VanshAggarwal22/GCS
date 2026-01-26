import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="CNG Daily Operations Dashboard",
    layout="wide"
)

st.title("📊 CNG Station Daily Dashboard")

# --------------------------------------------------
# LOAD DATA FROM GOOGLE SHEETS
# --------------------------------------------------
SHEET_ID = "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

df = pd.read_csv(CSV_URL)

# --------------------------------------------------
# CLEAN COLUMN NAMES (CRITICAL FIX)
# --------------------------------------------------
df.columns = (
    df.columns
    .str.strip()
    .str.upper()
    .str.replace(" ", "_")
)

# --------------------------------------------------
# AUTO-DETECT DATE COLUMN (NO HARD CODING)
# --------------------------------------------------
date_col = [c for c in df.columns if "DATE" in c][0]
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

df = df.dropna(subset=[date_col])

# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.header("🔎 Filters")

min_date = df[date_col].min()
max_date = df[date_col].max()

date_range = st.sidebar.date_input(
    "Select Date Range",
    [min_date, max_date]
)

filtered_df = df[
    (df[date_col] >= pd.to_datetime(date_range[0])) &
    (df[date_col] <= pd.to_datetime(date_range[1]))
]

# --------------------------------------------------
# SAFE COLUMN GETTER (PREVENTS CRASHES)
# --------------------------------------------------
def col(name):
    return filtered_df[name].sum() if name in filtered_df.columns else 0

# --------------------------------------------------
# KPI CALCULATIONS
# --------------------------------------------------
total_qty = col("DSR_QTY")
credit_sales = col("CREDIT_AMOUNT")
cash_deposit = col("CASH_DEPOSIT")
expenses = col("EXPENSE")
short_amt = col("SHORT_AMOUNT")

total_sales = (
    col("RTGS_AMOUNT")
    + col("ATM_AMOUNT")
    + col("PAYTM_AMOUNT")
    + cash_deposit
)

# --------------------------------------------------
# KPI DISPLAY
# --------------------------------------------------
k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("🔥 Total Gas Sold (KG)", f"{total_qty:,.0f}")
k2.metric("💰 Total Sales (₹)", f"{total_sales:,.0f}")
k3.metric("📉 Credit Sales (₹)", f"{credit_sales:,.0f}")
k4.metric("🏦 Cash Deposited (₹)", f"{cash_deposit:,.0f}")
k5.metric("💸 Expenses (₹)", f"{expenses:,.0f}")
k6.metric("⚠️ Short Amount (₹)", f"{short_amt:,.0f}")

st.divider()

# --------------------------------------------------
# SALES TREND
# --------------------------------------------------
if "DSR_QTY" in filtered_df.columns:
    st.subheader("📈 Daily Sales Trend")

    fig_sales = px.line(
        filtered_df,
        x=date_col,
        y="DSR_QTY",
        markers=True
    )
    st.plotly_chart(fig_sales, use_container_width=True)

# --------------------------------------------------
# SHIFT-WISE SALES
# --------------------------------------------------
shift_cols = [c for c in ["SHIFT_A_QTY", "SHIFT_B_QTY"] if c in filtered_df.columns]

if shift_cols:
    st.subheader("📊 Shift-wise Sales")

    shift_df = filtered_df[[date_col] + shift_cols]
    shift_df = shift_df.melt(date_col, var_name="Shift", value_name="Quantity")

    fig_shift = px.bar(
        shift_df,
        x=date_col,
        y="Quantity",
        color="Shift",
        barmode="group"
    )
    st.plotly_chart(fig_shift, use_container_width=True)

# --------------------------------------------------
# PAYMENT MODE BREAKDOWN
# --------------------------------------------------
payment_data = {
    "RTGS": col("RTGS_AMOUNT"),
    "ATM": col("ATM_AMOUNT"),
    "Paytm": col("PAYTM_AMOUNT"),
    "Cash": cash_deposit
}

payment_df = pd.DataFrame(
    [(k, v) for k, v in payment_data.items() if v > 0],
    columns=["Mode", "Amount"]
)

if not payment_df.empty:
    st.subheader("💳 Payment Mode Breakdown")

    fig_pay = px.pie(
        payment_df,
        names="Mode",
        values="Amount"
    )
    st.plotly_chart(fig_pay, use_container_width=True)

# --------------------------------------------------
# CASH RECONCILIATION
# --------------------------------------------------
st.subheader("🏦 Cash Reconciliation")

cash_df = pd.DataFrame({
    "Type": ["Cash Deposited", "Expenses", "Short Amount"],
    "Amount": [cash_deposit, expenses, short_amt]
})

fig_cash = px.bar(
    cash_df,
    x="Type",
    y="Amount"
)
st.plotly_chart(fig_cash, use_container_width=True)

# --------------------------------------------------
# OPERATIONAL EFFICIENCY
# --------------------------------------------------
if "FILLING_BOYS" in filtered_df.columns and "DSR_QTY" in filtered_df.columns:
    st.subheader("👷 Operational Efficiency")

    filtered_df["SALES_PER_BOY"] = (
        filtered_df["DSR_QTY"] / filtered_df["FILLING_BOYS"]
    )

    fig_eff = px.line(
        filtered_df,
        x=date_col,
        y="SALES_PER_BOY",
        markers=True
    )
    st.plotly_chart(fig_eff, use_container_width=True)

# --------------------------------------------------
# RAW DATA
# --------------------------------------------------
st.subheader("📄 Raw Data")
st.dataframe(filtered_df, use_container_width=True)
