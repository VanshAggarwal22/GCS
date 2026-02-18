import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="CNG Intelligence Dashboard",
    page_icon="🔥",
    layout="wide"
)

# =====================================================
# GOOGLE CONNECTION
# =====================================================
@st.cache_resource
def connect_google():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    service_account_info = dict(st.secrets["gcp_service_account"])
    service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=scope
    )

    return gspread.authorize(credentials)


client = connect_google()

# =====================================================
# FETCH SPREADSHEETS
# =====================================================
@st.cache_data(ttl=300)
def get_spreadsheets():
    return client.list_spreadsheet_files()


files = get_spreadsheets()

if not files:
    st.error("No spreadsheets found. Share sheet with service account email.")
    st.stop()

file_names = [file["name"] for file in files]
selected_file = st.sidebar.selectbox("Select Spreadsheet (Month)", file_names)

file_id = next(file["id"] for file in files if file["name"] == selected_file)

# =====================================================
# FETCH WORKSHEETS
# =====================================================
spreadsheet = client.open_by_key(file_id)
worksheets = spreadsheet.worksheets()
sheet_names = [ws.title for ws in worksheets]

if not sheet_names:
    st.error("No sheets found inside this spreadsheet.")
    st.stop()

selected_sheet = st.sidebar.selectbox("Select Date Sheet", sheet_names)

# =====================================================
# LOAD DATA (SAFE)
# =====================================================
@st.cache_data(ttl=300)
def load_data(spreadsheet_id, worksheet_name):
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)
    data = worksheet.get_all_values()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    if len(df) < 2:
        return pd.DataFrame()

    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)

    return df


df = load_data(file_id, selected_sheet)

if df.empty:
    st.warning("No usable data in this sheet.")
    st.stop()

# =====================================================
# SAFE NUMERIC CLEANING (NO .str ERROR)
# =====================================================
for col in df.columns:
    df[col] = pd.to_numeric(
        df[col].astype(str).str.replace(",", "", regex=False),
        errors="ignore"
    )

# =====================================================
# REMOVE TOTAL ROW (IF EXISTS)
# =====================================================
if "SHIFT" in df.columns:
    df_clean = df[~df["SHIFT"].astype(str).str.contains("TOTAL", case=False, na=False)]
else:
    df_clean = df.copy()

numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
totals = df_clean[numeric_cols].sum() if numeric_cols else pd.Series()

# =====================================================
# COLUMN AUTO DETECTION
# =====================================================
def find_col(keyword):
    for col in df.columns:
        if keyword in col.upper():
            return col
    return None

qty_col = find_col("QTY")
sale_col = find_col("SALE")
cash_col = find_col("CASH")
paytm_col = find_col("PAYTM")
credit_col = find_col("CREDIT")
atm_col = find_col("ATM")
collection_col = find_col("TOTAL")

# =====================================================
# DASHBOARD UI
# =====================================================
st.title(f"🔥 CNG Dashboard - {selected_file}")
st.subheader(f"📅 Date: {selected_sheet}")
st.divider()

k1, k2, k3, k4, k5, k6, k7 = st.columns(7)

k1.metric("Gas Sold (KG)", f"{totals.get(qty_col,0):,.0f}" if qty_col else "0")
k2.metric("Sale Amount (₹)", f"{totals.get(sale_col,0):,.0f}" if sale_col else "0")
k3.metric("Cash (₹)", f"{totals.get(cash_col,0):,.0f}" if cash_col else "0")
k4.metric("Paytm (₹)", f"{totals.get(paytm_col,0):,.0f}" if paytm_col else "0")
k5.metric("Credit (₹)", f"{totals.get(credit_col,0):,.0f}" if credit_col else "0")
k6.metric("ATM (₹)", f"{totals.get(atm_col,0):,.0f}" if atm_col else "0")
k7.metric("Total Collection (₹)", f"{totals.get(collection_col,0):,.0f}" if collection_col else "0")

# =====================================================
# PAYMENT MIX
# =====================================================
payment_cols = [cash_col, paytm_col, credit_col, atm_col]
payment_cols = [col for col in payment_cols if col and col in df_clean.columns]

if payment_cols:
    st.divider()
    st.subheader("💳 Payment Mix")

    payment_data = df_clean[payment_cols].sum().reset_index()
    payment_data.columns = ["Mode", "Amount"]

    fig_pie = px.pie(
        payment_data,
        names="Mode",
        values="Amount",
        hole=0.4
    )

    st.plotly_chart(fig_pie, use_container_width=True)

# =====================================================
# SHIFT COMPARISON
# =====================================================
if "SHIFT" in df_clean.columns and numeric_cols:
    st.divider()
    st.subheader("📊 Shift Comparison")

    fig_bar = px.bar(
        df_clean,
        x="SHIFT",
        y=numeric_cols,
        barmode="group"
    )

    st.plotly_chart(fig_bar, use_container_width=True)

# =====================================================
# MONTHLY GAS TREND
# =====================================================
st.divider()
st.subheader("📈 Monthly Gas Trend")

monthly_data = []

for ws in worksheets:
    try:
        temp_df = load_data(file_id, ws.title)

        if temp_df.empty:
            continue

        for col in temp_df.columns:
            temp_df[col] = pd.to_numeric(
                temp_df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce"
            )

        if qty_col and qty_col in temp_df.columns:
            total_qty = temp_df[qty_col].sum()
            monthly_data.append({"Date": ws.title, "Gas Sold": total_qty})

    except Exception:
        continue

if monthly_data:
    monthly_df = pd.DataFrame(monthly_data)

    fig_line = px.line(
        monthly_df,
        x="Date",
        y="Gas Sold",
        markers=True
    )

    st.plotly_chart(fig_line, use_container_width=True)

# =====================================================
# RAW DATA
# =====================================================
st.divider()
st.subheader("📄 Raw Data")
st.dataframe(df, use_container_width=True)
