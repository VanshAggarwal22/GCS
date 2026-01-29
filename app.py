import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import re

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="Gas Sales Dashboard", layout="wide")
GOOGLE_SHEET_ID = "1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA"

# -------------------------
# HELPER FUNCTIONS
# -------------------------

# Get all GIDs from the Google Sheet
@st.cache_data(show_spinner=False)
def get_all_gids(sheet_id):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?&tqx=out:json"
    res = requests.get(url).text
    gids = re.findall(r"gid\":(\d+)", res)
    return list(set(gids))

# Load sheet, slice only rows 7-14 and columns AA-AI
def load_sheet_metrics(sheet_id, gid):
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(csv_url, header=None)
    except Exception as e:
        st.warning(f"Could not load GID {gid}: {e}")
        return pd.DataFrame()

    # Slice rows 7-14 (zero-indexed 6:14) and columns AA-AI (zero-indexed 26:35)
    df_slice = df.iloc[6:14, 26:35]

    # Assign column names
    columns = ["SHIFT", "QTY", "SALE_AMOUNT", "CASH", "PAYTM", "ATM",
               "CREDIT_SALE", "TOTAL_COLLECTION", "DIFF"]
    df_slice.columns = columns

    # Drop empty rows
    df_slice = df_slice.dropna(how="all", subset=columns)

    # Forward-fill SHIFT
    df_slice["SHIFT"] = df_slice["SHIFT"].ffill()

    # Convert numeric columns
    num_cols = ["QTY", "SALE_AMOUNT", "CASH", "PAYTM", "ATM", "CREDIT_SALE",
                "TOTAL_COLLECTION", "DIFF"]
    for c in num_cols:
        df_slice[c] = df_slice[c].astype(str).str.replace(",", "").astype(float)

    # Mark TOTAL rows
    df_slice["IS_TOTAL"] = df_slice["SHIFT"].str.contains("TOTAL", case=False)

    return df_slice

# Load all sheets
@st.cache_data(show_spinner=False)
def load_all_sheets(sheet_id):
    gids = get_all_gids(sheet_id)
    df_list = []
    for gid in gids:
        df_sheet = load_sheet_metrics(sheet_id, gid)
        if not df_sheet.empty:
            df_list.append(df_sheet)
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    else:
        return pd.DataFrame()

# -------------------------
# LOAD DATA
# -------------------------
df = load_all_sheets(GOOGLE_SHEET_ID)

if df.empty:
    st.error("❌ No metrics found in the specified range across all sheets.")
    st.stop()

# -------------------------
# SIDEBAR FILTERS
# -------------------------
shift_options = df["SHIFT"].unique().tolist()
selected_shifts = st.sidebar.multiselect("Select Shifts", options=shift_options, default=shift_options)
fdf = df[df["SHIFT"].isin(selected_shifts)]

# -------------------------
# DASHBOARD TABS
# -------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Shift-wise QTY & Sales",
    "💰 Payment Breakdown",
    "📈 Total Collection vs Diff",
    "📋 Raw Data"
])

# -------------------------
# TAB 1: SHIFT-wise QTY & Sales
# -------------------------
with tab1:
    st.subheader("Shift-wise Quantity & Sales")
    fig1 = px.bar(
        fdf,
        x="SHIFT",
        y=["QTY", "SALE_AMOUNT"],
        barmode="group",
        text_auto=True,
        title="Shift-wise Gas Quantity and Sale Amount"
    )
    st.plotly_chart(fig1, use_container_width=True)

# -------------------------
# TAB 2: PAYMENT BREAKDOWN
# -------------------------
with tab2:
    st.subheader("Payment Method Breakdown")
    payment_cols = ["CASH", "PAYTM", "ATM", "CREDIT_SALE"]
    fig2 = px.bar(
        fdf,
        x="SHIFT",
        y=payment_cols,
        barmode="stack",
        text_auto=True,
        title="Shift-wise Payment Methods"
    )
    st.plotly_chart(fig2, use_container_width=True)

# -------------------------
# TAB 3: TOTAL COLLECTION vs DIFF
# -------------------------
with tab3:
    st.subheader("Total Collection vs Difference")
    fig3 = px.bar(
        fdf,
        x="SHIFT",
        y=["TOTAL_COLLECTION", "DIFF"],
        barmode="group",
        text_auto=True,
        title="Shift-wise Total Collection vs Difference"
    )
    st.plotly_chart(fig3, use_container_width=True)

# -------------------------
# TAB 4: RAW DATA
# -------------------------
with tab4:
    st.subheader("Raw Extracted Data")
    st.dataframe(fdf, use_container_width=True)
