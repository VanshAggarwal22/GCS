import streamlit as st
import pandas as pd
import plotly.express as px

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="CNG Daily Operations Dashboard",
    layout="wide"
)

st.title("📊 CNG Station Daily Operations Dashboard")

# ==================================================
# LOAD DATA FROM GOOGLE SHEETS (CSV EXPORT)
# ==================================================
SHEET_ID = "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

raw = pd.read_csv(CSV_URL, header=2)

# ==================================================
# FIX HEADER ROW
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

# ==================================================
# MAKE COLUMN NAMES UNIQUE (SAFE)
# ==================================================
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

# ==================================================
# KEEP ONLY VALID SHIFT ROWS
# ==================================================
df["SHIFT"] = df["SHIFT"].astype(str).str.strip()
df = df[df["SHIFT"].isin(["A", "B", "C"])]

# ==================================================
# DATE HANDLING (CRITICAL)
# ==================================================
df["DATE"] = df["DATE"].ffill()
df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
df = df.dropna(subset=["DATE"])

# ==================================================
# CLEAN NUMERIC COLUMNS
# ==================================================
for col in df.columns:
    if col not in ["DATE", "SHIFT"]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .replace("nan", "0")
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# ==================================================
# DAILY AGGREGATION (ALL DATES FIXED)
# ==================================================
daily = df.groupby("DATE", as_index=False).sum(numeric_only=True)

# ==================================================
# SIDEBAR FILTERS
# ==================================================
st.sidebar.header("🔎 Filters")

date_range = st.sidebar.date_input(
    "Select Date Range",
    [daily["DATE"].min(), daily["DATE"].max()]
)

daily = daily[
    (daily["DATE"] >= pd.to_datetime(date_range[0])) &
    (daily["DATE"] <= pd.to_datetime(date_range[1]))
]

# ==================================================
# SAFE SUM FUNCTION
# ==================================================
def safe(col):
    return daily[col].sum() if col in daily.columns else 0

# ==================================================
# TARGET INPUT
# ==================================================
st.sidebar.divider()
st.sidebar.subheader("🎯 Daily Target")

target = st.sidebar.number_input(
    "Target Gas Sale (KG)",
    min_value=0,
    value=1000
)

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

k1.metric("🔥 Total Gas Sold (KG)", f"{safe('TOTAL DSR QTY. KG'):,.0f}")
k2.metric("💳 Credit Sales (₹)", f"{safe('CREDIT SALE (RS.)'):,.0f}")
k3.metric("💰 Paytm (₹)", f"{safe('PAYTM'):,.0f}")
k4.metric("🏦 Cash Deposited (₹)", f"{safe('CASH DEPOSIIT IN BANK'):,.0f}")
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
    "🚨 Alerts & Exceptions",
    "📄 Raw Data"
])

# ==================================================
# TAB 1: DAILY OVERVIEW
# ==================================================
with tabs[0]:
    if "TOTAL DSR QTY. KG" in daily.columns:
        fig_qty = px.line(
            daily,
            x="DATE",
            y="TOTAL DSR QTY. KG",
            markers=True,
            title="Daily Gas Sales (KG)"
        )
        st.plotly_chart(fig_qty, use_container_width=True)

    payment_df = pd.DataFrame({
        "Mode": ["ATM", "Paytm", "Cash Deposit"],
        "Amount": [
            safe("ATM"),
            safe("PAYTM"),
            safe("CASH DEPOSIIT IN BANK")
        ]
    }).query("Amount > 0")

    fig_pay = px.pie(
        payment_df,
        names="Mode",
        values="Amount",
        title="Payment Mode Split"
    )
    st.plotly_chart(fig_pay, use_container_width=True)

# ==================================================
# TAB 2: SHIFT ANALYSIS
# ==================================================
with tabs[1]:
    shift_daily = df.groupby(["DATE", "SHIFT"], as_index=False).sum(numeric_only=True)

    if "TOTAL DSR QTY. KG" in shift_daily.columns:
        fig_shift = px.bar(
            shift_daily,
            x="DATE",
            y="TOTAL DSR QTY. KG",
            color="SHIFT",
            barmode="group",
            title="Gas Sales by Shift (A / B / C)"
        )
        st.plotly_chart(fig_shift, use_container_width=True)

    shift_total = df.groupby("SHIFT", as_index=False).sum(numeric_only=True)

    fig_shift_total = px.pie(
        shift_total,
        names="SHIFT",
        values="TOTAL DSR QTY. KG",
        title="Total Contribution by Shift"
    )
    st.plotly_chart(fig_shift_total, use_container_width=True)

# ==================================================
# TAB 3: MONTHLY SUMMARY
# ==================================================
with tabs[2]:
    daily["MONTH"] = daily["DATE"].dt.to_period("M").astype(str)
    monthly = daily.groupby("MONTH", as_index=False).sum(numeric_only=True)

    st.dataframe(monthly, use_container_width=True)

    fig_month = px.bar(
        monthly,
        x="MONTH",
        y="TOTAL DSR QTY. KG",
        title="Monthly Gas Sales"
    )
    st.plotly_chart(fig_month, use_container_width=True)

# ==================================================
# TAB 4: ALERTS & EXCEPTIONS
# ==================================================
with tabs[3]:
    short_amt = safe("SHORT AMOUNT")
    expenses = safe("EXPENSES")
    deposit = safe("CASH DEPOSIIT IN BANK")

    if short_amt > 0:
        st.error(f"🚨 Short Amount Detected: ₹{short_amt:,.0f}")
    else:
        st.success("✅ No Short Amount")

    if expenses > deposit * 0.2 and deposit > 0:
        st.warning(f"⚠️ Expenses unusually high: ₹{expenses:,.0f}")
    else:
        st.success("💰 Expenses within normal range")

# ==================================================
# TAB 5: RAW DATA
# ==================================================
with tabs[4]:
    st.dataframe(daily, use_container_width=True)
