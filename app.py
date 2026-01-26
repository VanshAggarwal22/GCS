import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="CNG Daily Operations Dashboard",
    layout="wide"
)

# ---------------- LOAD DATA ----------------
SHEET_ID = "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

df = pd.read_csv(CSV_URL)
df.columns = df.columns.str.strip().str.upper()

df["DATE"] = pd.to_datetime(df["DATE"])

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.title("🔎 Filters")

date_range = st.sidebar.date_input(
    "Select Date Range",
    [df["DATE"].min(), df["DATE"].max()]
)

filtered_df = df[
    (df["DATE"] >= pd.to_datetime(date_range[0])) &
    (df["DATE"] <= pd.to_datetime(date_range[1]))
]

# ---------------- KPI CALCULATIONS ----------------
total_qty = filtered_df["DSR_QTY"].sum()
total_sales = (
    filtered_df["RTGS_AMOUNT"].sum()
    + filtered_df["ATM_AMOUNT"].sum()
    + filtered_df["PAYTM_AMOUNT"].sum()
    + filtered_df["CASH_DEPOSIT"].sum()
)

credit_sales = filtered_df["CREDIT_AMOUNT"].sum()
cash_deposit = filtered_df["CASH_DEPOSIT"].sum()
expenses = filtered_df["EXPENSE"].sum()
short_amt = filtered_df["SHORT_AMOUNT"].sum()

# ---------------- KPI ROW ----------------
st.title("📊 CNG Station Daily Dashboard")

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("🔥 Total Gas Sold (KG)", f"{total_qty:,.0f}")
col2.metric("💰 Total Sales (₹)", f"{total_sales:,.0f}")
col3.metric("📉 Credit Sales (₹)", f"{credit_sales:,.0f}")
col4.metric("🏦 Cash Deposited (₹)", f"{cash_deposit:,.0f}")
col5.metric("💸 Expenses (₹)", f"{expenses:,.0f}")
col6.metric("⚠️ Short Amount (₹)", f"{short_amt:,.0f}")

st.divider()

# ---------------- SALES TREND ----------------
st.subheader("📈 Daily Sales Trend")

fig_sales = px.line(
    filtered_df,
    x="DATE",
    y="DSR_QTY",
    markers=True
)
st.plotly_chart(fig_sales, use_container_width=True)

# ---------------- SHIFT ANALYSIS ----------------
st.subheader("📊 Shift-wise Sales")

shift_df = filtered_df[["DATE", "SHIFT_A_QTY", "SHIFT_B_QTY"]]
shift_df = shift_df.melt("DATE", var_name="Shift", value_name="Quantity")

fig_shift = px.bar(
    shift_df,
    x="DATE",
    y="Quantity",
    color="Shift",
    barmode="group"
)
st.plotly_chart(fig_shift, use_container_width=True)

# ---------------- PAYMENT MODE ----------------
st.subheader("💳 Payment Mode Breakdown")

payment_df = pd.DataFrame({
    "Mode": ["RTGS", "ATM", "Paytm", "Cash"],
    "Amount": [
        filtered_df["RTGS_AMOUNT"].sum(),
        filtered_df["ATM_AMOUNT"].sum(),
        filtered_df["PAYTM_AMOUNT"].sum(),
        filtered_df["CASH_DEPOSIT"].sum()
    ]
})

fig_pay = px.pie(
    payment_df,
    names="Mode",
    values="Amount"
)
st.plotly_chart(fig_pay, use_container_width=True)

# ---------------- CASH RECONCILIATION ----------------
st.subheader("🏦 Cash Reconciliation")

cash_df = pd.DataFrame({
    "Type": ["Cash Deposited", "Expenses", "Short Amount"],
    "Amount": [
        cash_deposit,
        expenses,
        short_amt
    ]
})

fig_cash = px.bar(
    cash_df,
    x="Type",
    y="Amount"
)
st.plotly_chart(fig_cash, use_container_width=True)

# ---------------- OPERATIONAL METRICS ----------------
st.subheader("👷 Operational Efficiency")

filtered_df["SALES_PER_BOY"] = filtered_df["DSR_QTY"] / filtered_df["FILLING_BOYS"]

fig_eff = px.line(
    filtered_df,
    x="DATE",
    y="SALES_PER_BOY",
    markers=True
)
st.plotly_chart(fig_eff, use_container_width=True)

# ---------------- DATA TABLE ----------------
st.subheader("📄 Raw Data")
st.dataframe(filtered_df, use_container_width=True)
