import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# --------------------------------
# CONFIG
# --------------------------------
st.set_page_config(page_title="Gas Sales Dashboard", layout="wide")

SPREADSHEET_ID = "1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA"
SERVICE_ACCOUNT_FILE = "service_account.json"

# Fixed layout
ROW_START = 6     # row 7 (0-indexed)
ROW_END = 14      # row 14
COL_START = 26    # AA
COL_END = 35      # AI

COLUMNS = [
    "SHIFT", "QTY", "SALE_AMOUNT", "CASH",
    "PAYTM", "ATM", "CREDIT_SALE",
    "TOTAL_COLLECTION", "DIFF"
]

# --------------------------------
# AUTHENTICATION
# --------------------------------
@st.cache_resource
def get_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=scopes
    )
    return gspread.authorize(creds)

client = get_client()
spreadsheet = client.open_by_key(SPREADSHEET_ID)

# --------------------------------
# LOAD DATA FROM ALL SHEETS
# --------------------------------
@st.cache_data(show_spinner=False)
def load_all_sheets():
    all_data = []

    for ws in spreadsheet.worksheets():
        sheet_name = ws.title  # used as DATE

        raw = ws.get_all_values()

        if len(raw) < ROW_END:
            continue

        block = raw[ROW_START:ROW_END]
        df = pd.DataFrame(block, columns=COLUMNS)

        df = df.dropna(how="all")
        df["SHIFT"] = df["SHIFT"].replace("", pd.NA).ffill()
        df["DATE"] = sheet_name

        num_cols = COLUMNS[1:]
        for col in num_cols:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "")
                .replace("", "0")
                .astype(float)
            )

        df["IS_TOTAL"] = df["SHIFT"].str.contains("TOTAL", case=False)
        all_data.append(df)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)

df = load_all_sheets()

if df.empty:
    st.error("❌ No data found in AA–AI (rows 7–14) across sheets.")
    st.stop()

# --------------------------------
# SIDEBAR FILTERS
# --------------------------------
st.sidebar.header("Filters")

dates = sorted(df["DATE"].unique())
selected_dates = st.sidebar.multiselect("Select Dates", dates, default=dates)

shifts = sorted(df["SHIFT"].unique())
selected_shifts = st.sidebar.multiselect("Select Shifts", shifts, default=shifts)

fdf = df[
    (df["DATE"].isin(selected_dates)) &
    (df["SHIFT"].isin(selected_shifts))
]

# --------------------------------
# KPI METRICS
# --------------------------------
total_qty = fdf["QTY"].sum()
total_sales = fdf["SALE_AMOUNT"].sum()
total_collection = fdf["TOTAL_COLLECTION"].sum()
total_diff = fdf["DIFF"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Qty (KG)", f"{total_qty:,.2f}")
c2.metric("Total Sales", f"₹ {total_sales:,.2f}")
c3.metric("Total Collection", f"₹ {total_collection:,.2f}")
c4.metric("Total Difference", f"₹ {total_diff:,.2f}")

# --------------------------------
# TABS
# --------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Shift-wise Performance",
    "💰 Payment Breakdown",
    "📈 Daily Trends",
    "📋 Raw Data"
])

# --------------------------------
# TAB 1 — SHIFT-WISE
# --------------------------------
with tab1:
    fig1 = px.bar(
        fdf,
        x="SHIFT",
        y=["QTY", "SALE_AMOUNT"],
        barmode="group",
        facet_col="DATE",
        title="Shift-wise Quantity & Sales"
    )
    st.plotly_chart(fig1, use_container_width=True)

# --------------------------------
# TAB 2 — PAYMENTS
# --------------------------------
with tab2:
    fig2 = px.bar(
        fdf,
        x="SHIFT",
        y=["CASH", "PAYTM", "ATM", "CREDIT_SALE"],
        barmode="stack",
        facet_col="DATE",
        title="Payment Method Breakdown"
    )
    st.plotly_chart(fig2, use_container_width=True)

# --------------------------------
# TAB 3 — DAILY TRENDS
# --------------------------------
with tab3:
    daily = fdf.groupby("DATE").agg(
        TOTAL_QTY=("QTY", "sum"),
        TOTAL_SALES=("SALE_AMOUNT", "sum"),
        TOTAL_COLLECTION=("TOTAL_COLLECTION", "sum"),
        TOTAL_DIFF=("DIFF", "sum")
    ).reset_index()

    fig3 = px.line(
        daily,
        x="DATE",
        y=["TOTAL_SALES", "TOTAL_COLLECTION"],
        markers=True,
        title="Daily Sales vs Collection"
    )
    st.plotly_chart(fig3, use_container_width=True)

# --------------------------------
# TAB 4 — RAW DATA
# --------------------------------
with tab4:
    st.dataframe(fdf, use_container_width=True)
