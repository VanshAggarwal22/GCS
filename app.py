import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import re

st.set_page_config(page_title="Gas Sales Dashboard", layout="wide")

# -------------------------
# CONFIG
# -------------------------
GOOGLE_SHEET_ID = "1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA"
SHEET_RANGE = "AA7:AI14"  # fixed range with metrics

# -------------------------
# HELPER FUNCTIONS
# -------------------------

# Get all sheet GIDs
@st.cache_data(show_spinner=False)
def get_all_gids(sheet_id):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?&tqx=out:json"
    res = requests.get(url).text
    gids = re.findall(r"gid\":(\d+)", res)
    return list(set(gids))

# Load only the relevant range from a sheet
def load_sheet_range(sheet_id, gid, sheet_range):
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}&range={sheet_range}"
    try:
        df = pd.read_csv(csv_url, header=None)
    except Exception as e:
        st.warning(f"Could not load GID {gid}: {e}")
        return pd.DataFrame()
    return df

# Combine all sheets into one DataFrame
@st.cache_data(show_spinner=False)
def load_all_sheets(sheet_id, sheet_range):
    all_gids = get_all_gids(sheet_id)
    df_list = []
    for gid in all_gids:
        df_sheet = load_sheet_range(sheet_id, gid, sheet_range)
        if df_sheet.empty:
            continue
        df_list.append(df_sheet)
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    else:
        return pd.DataFrame()

# -------------------------
# LOAD DATA
# -------------------------
raw_df = load_all_sheets(GOOGLE_SHEET_ID, SHEET_RANGE)

if raw_df.empty:
    st.error("❌ No data found in the selected range across all sheets.")
    st.stop()

# -------------------------
# CLEAN DATA
# -------------------------
# Assign proper column names
columns = ["SHIFT", "QTY", "SALE_AMOUNT", "CASH", "PAYTM", "ATM", "CREDIT_SALE", "TOTAL_COLLECTION", "DIFF"]
df = raw_df.iloc[:, :len(columns)]
df.columns = columns

# Drop empty rows
df = df.dropna(how="all", subset=columns)

# Forward-fill SHIFT (because sometimes SHIFT row is blank)
df["SHIFT"] = df["SHIFT"].ffill()

# Convert numeric columns safely (remove commas)
num_cols = ["QTY", "SALE_AMOUNT", "CASH", "PAYTM", "ATM", "CREDIT_SALE", "TOTAL_COLLECTION", "DIFF"]
for c in num_cols:
    df[c] = df[c].astype(str).str.replace(",", "").astype(float)

# Mark TOTAL rows
df["IS_TOTAL"] = df["SHIFT"].str.contains("TOTAL", case=False)

# -------------------------
# SIDEBAR FILTER
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
