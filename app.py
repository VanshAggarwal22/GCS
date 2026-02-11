import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import timedelta

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="CNG Intelligence Dashboard", layout="wide")

# --------------------------------------------------
# MONTHLY SHEETS
# --------------------------------------------------
MONTHLY_SHEETS = {
    "January 2026": "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM",
    "February 2026": "1bZBzVx1oJUXf4tBIpgJwJan8iwh7alz9CO9Z_5TMB3I"
}

# Session storage for daily GID mapping
if "daily_gid_map" not in st.session_state:
    st.session_state.daily_gid_map = {}

# --------------------------------------------------
# COMMON LOAD + CLEAN FUNCTION
# --------------------------------------------------
def load_sheet(sheet_id, gid=None):

    if gid:
        CSV_URL = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    else:
        CSV_URL = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    raw = pd.read_csv(CSV_URL, header=2)

    raw.columns = raw.iloc[0]
    df = raw.iloc[1:].copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace("\n", " ")
    )

    # Make columns unique
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

    # Filter shifts
    df["SHIFT"] = df["SHIFT"].astype(str).str.strip()
    df = df[df["SHIFT"].isin(["A", "B", "C"])]

    # Fix date
    df["DATE"] = df["DATE"].ffill()
    df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["DATE"])

    # Clean numeric
    for col in df.columns:
        if col not in ["DATE", "SHIFT"]:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", "", regex=False)
                .replace("nan", "0")
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


# --------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------
st.sidebar.title("📊 Navigation")
page = st.sidebar.radio(
    "Select View",
    ["Daily GID Entry",
     "Daily Dashboard",
     "Monthly Dashboard"]
)

# ==================================================
# 1️⃣ DAILY GID ENTRY
# ==================================================
if page == "Daily GID Entry":

    st.title("📅 Daily GID Mapping")

    selected_month = st.selectbox(
        "Select Month Source",
        list(MONTHLY_SHEETS.keys())
    )

    selected_date = st.date_input("Select Date")
    gid_input = st.text_input("Enter GID")

    if st.button("Save Mapping"):
        if gid_input:
            st.session_state.daily_gid_map[str(selected_date)] = {
                "sheet_id": MONTHLY_SHEETS[selected_month],
                "gid": gid_input
            }
            st.success("Mapping saved successfully")

    st.subheader("Saved Mappings")
    st.write(st.session_state.daily_gid_map)


# ==================================================
# 2️⃣ DAILY DASHBOARD
# ==================================================
if page == "Daily Dashboard":

    st.title("📈 Daily Operations Dashboard")

    if not st.session_state.daily_gid_map:
        st.warning("No daily GIDs saved yet.")
    else:

        selected_date = st.selectbox(
            "Select Date",
            list(st.session_state.daily_gid_map.keys())
        )

        mapping = st.session_state.daily_gid_map[selected_date]
        sheet_id = mapping["sheet_id"]
        gid = mapping["gid"]

        df = load_sheet(sheet_id, gid)

        # Aggregate daily
        daily = df.groupby("DATE", as_index=False).sum(numeric_only=True)

        def safe(col):
            return daily[col].sum() if col in daily.columns else 0

        st.subheader("📊 Daily KPIs")

        k1, k2, k3, k4, k5 = st.columns(5)

        k1.metric("🔥 Total Gas Sold (KG)", f"{safe('TOTAL DSR QTY. KG'):,.0f}")
        k2.metric("💳 Credit Sales (₹)", f"{safe('CREDIT SALE (RS.)'):,.0f}")
        k3.metric("💰 Paytm (₹)", f"{safe('PAYTM'):,.0f}")
        k4.metric("🏦 Cash Deposit (₹)", f"{safe('CASH DEPOSIIT IN BANK'):,.0f}")
        k5.metric("⚠️ Short Amount (₹)", f"{safe('SHORT AMOUNT'):,.0f}")

        st.divider()

        if "TOTAL DSR QTY. KG" in daily.columns:
            fig = px.bar(
                daily,
                x="DATE",
                y="TOTAL DSR QTY. KG",
                title="Gas Sold (Daily)"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📄 Raw Daily Data")
        st.dataframe(daily, use_container_width=True)


# ==================================================
# 3️⃣ MONTHLY DASHBOARD
# ==================================================
if page == "Monthly Dashboard":

    st.title("🚀 Monthly Operations Dashboard")

    selected_month = st.selectbox(
        "Select Month",
        list(MONTHLY_SHEETS.keys())
    )

    df = load_sheet(MONTHLY_SHEETS[selected_month])

    # Aggregate daily
    daily = df.groupby("DATE", as_index=False).sum(numeric_only=True)

    # Sidebar Date Filter
    st.sidebar.header("🔎 Date Filter")
    date_range = st.sidebar.date_input(
        "Select Date Range",
        [daily["DATE"].min(), daily["DATE"].max()]
    )

    daily = daily[
        (daily["DATE"] >= pd.to_datetime(date_range[0])) &
        (daily["DATE"] <= pd.to_datetime(date_range[1]))
    ]

    def safe(col):
        return daily[col].sum() if col in daily.columns else 0

    st.subheader("📊 Monthly KPIs")

    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric("🔥 Total Gas Sold (KG)", f"{safe('TOTAL DSR QTY. KG'):,.0f}")
    k2.metric("💳 Credit Sales (₹)", f"{safe('CREDIT SALE (RS.)'):,.0f}")
    k3.metric("💰 Paytm (₹)", f"{safe('PAYTM'):,.0f}")
    k4.metric("🏦 Cash Deposit (₹)", f"{safe('CASH DEPOSIIT IN BANK'):,.0f}")
    k5.metric("⚠️ Short Amount (₹)", f"{safe('SHORT AMOUNT'):,.0f}")

    st.divider()

    if "TOTAL DSR QTY. KG" in daily.columns:
        fig = px.line(
            daily,
            x="DATE",
            y="TOTAL DSR QTY. KG",
            markers=True,
            title="Monthly Gas Sales Trend"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📄 Cleaned Monthly Data")
    st.dataframe(daily, use_container_width=True)
