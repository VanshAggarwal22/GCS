import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Performance Dashboard", layout="wide")

# =====================================================
# GOOGLE AUTH USING STREAMLIT SECRETS
# =====================================================
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

client = gspread.authorize(credentials)

# =====================================================
# LOAD SPREADSHEET LIST (MONTHS)
# =====================================================
@st.cache_data
def list_spreadsheets():
    files = client.list_spreadsheet_files()
    return {file["name"]: file["id"] for file in files}

# =====================================================
# LOAD WORKSHEET NAMES (DATES)
# =====================================================
@st.cache_data
def list_worksheets(spreadsheet_id):
    spreadsheet = client.open_by_key(spreadsheet_id)
    return [ws.title for ws in spreadsheet.worksheets()]

# =====================================================
# LOAD DATA FROM SHEET
# =====================================================
@st.cache_data
def load_data(spreadsheet_id, worksheet_name):
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

# =====================================================
# SIDEBAR SELECTION
# =====================================================
st.sidebar.title("Select Data")

spreadsheets = list_spreadsheets()

if not spreadsheets:
    st.error("No spreadsheets found.")
    st.stop()

selected_month = st.sidebar.selectbox(
    "Select Spreadsheet (Month)",
    list(spreadsheets.keys())
)

spreadsheet_id = spreadsheets[selected_month]

worksheets = list_worksheets(spreadsheet_id)

selected_date = st.sidebar.selectbox(
    "Select Date Sheet",
    worksheets
)

# =====================================================
# LOAD DATA
# =====================================================
df = load_data(spreadsheet_id, selected_date)

if df.empty:
    st.warning("No data available in selected sheet.")
    st.stop()

# =====================================================
# SAFE NUMERIC CLEANING (NO .str ACCESSOR USED)
# =====================================================
for col in df.columns:
    df[col] = df[col].astype(str).replace(",", "", regex=True)
    df[col] = pd.to_numeric(df[col], errors="ignore")

# =====================================================
# DASHBOARD TITLE
# =====================================================
st.title("📊 Performance Dashboard")
st.subheader(f"{selected_month} | {selected_date}")

# =====================================================
# AUTO METRIC CALCULATION
# =====================================================

numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

if not numeric_cols:
    st.warning("No numeric columns found to calculate metrics.")
else:
    total_metrics = {}

    for col in numeric_cols:
        total_metrics[col] = df[col].sum()

    # Display metrics in columns
    cols = st.columns(min(4, len(total_metrics)))

    for i, (metric_name, value) in enumerate(total_metrics.items()):
        cols[i % len(cols)].metric(
            label=metric_name,
            value=f"{value:,.2f}"
        )

# =====================================================
# DATA TABLE
# =====================================================
st.markdown("---")
st.subheader("Raw Data")
st.dataframe(df, use_container_width=True)
