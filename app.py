import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Performance Dashboard", layout="wide")

# =====================================================
# GOOGLE AUTH
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
# LIST SPREADSHEETS
# =====================================================
@st.cache_data
def list_spreadsheets():
    files = client.list_spreadsheet_files()
    return {file["name"]: file["id"] for file in files}

# =====================================================
# LIST WORKSHEETS
# =====================================================
@st.cache_data
def list_worksheets(spreadsheet_id):
    spreadsheet = client.open_by_key(spreadsheet_id)
    return [ws.title for ws in spreadsheet.worksheets()]

# =====================================================
# LOAD CONSOLIDATE METRICS
# =====================================================
@st.cache_data
def load_consolidated_metrics(spreadsheet_id, worksheet_name):
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)

    raw = worksheet.get_all_values()

    if not raw:
        return {}, None

    df = pd.DataFrame(raw)

    consolidate_row = None
    consolidate_col = None

    # Flexible search
    for r in range(len(df)):
        for c in range(len(df.columns)):
            cell_value = str(df.iloc[r, c]).strip().upper()
            if "CONSOLIDATE" in cell_value:
                consolidate_row = r
                consolidate_col = c
                break
        if consolidate_row is not None:
            break

    if consolidate_row is None:
        return {}, df.head(25)

    def safe_float(value):
        try:
            return float(str(value).replace(",", "").strip())
        except:
            return 0.0

    try:
        shift_a_row = consolidate_row + 2
        shift_b_row = consolidate_row + 4

        metrics = {
            # SHIFT A
            "SHIFT_A_QTY": safe_float(df.iloc[shift_a_row, consolidate_col+1]),
            "SHIFT_A_SALE": safe_float(df.iloc[shift_a_row, consolidate_col+2]),
            "SHIFT_A_CASH": safe_float(df.iloc[shift_a_row, consolidate_col+3]),
            "SHIFT_A_PAYTM": safe_float(df.iloc[shift_a_row, consolidate_col+4]),
            "SHIFT_A_ATM": safe_float(df.iloc[shift_a_row, consolidate_col+5]),
            "SHIFT_A_CREDIT": safe_float(df.iloc[shift_a_row, consolidate_col+6]),
            "SHIFT_A_TOTAL": safe_float(df.iloc[shift_a_row, consolidate_col+7]),
            "SHIFT_A_DIFF": safe_float(df.iloc[shift_a_row, consolidate_col+8]),

            # SHIFT B
            "SHIFT_B_QTY": safe_float(df.iloc[shift_b_row, consolidate_col+1]),
            "SHIFT_B_SALE": safe_float(df.iloc[shift_b_row, consolidate_col+2]),
            "SHIFT_B_CASH": safe_float(df.iloc[shift_b_row, consolidate_col+3]),
            "SHIFT_B_PAYTM": safe_float(df.iloc[shift_b_row, consolidate_col+4]),
            "SHIFT_B_ATM": safe_float(df.iloc[shift_b_row, consolidate_col+5]),
            "SHIFT_B_CREDIT": safe_float(df.iloc[shift_b_row, consolidate_col+6]),
            "SHIFT_B_TOTAL": safe_float(df.iloc[shift_b_row, consolidate_col+7]),
            "SHIFT_B_DIFF": safe_float(df.iloc[shift_b_row, consolidate_col+8]),
        }

    except:
        return {}, df.head(25)

    return metrics, None

# =====================================================
# SIDEBAR
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
metrics, debug_df = load_consolidated_metrics(spreadsheet_id, selected_date)

if not metrics:
    st.error("Could not extract CONSOLIDATE DATA section.")

    if debug_df is not None:
        st.subheader("Sheet Preview (Debug)")
        st.dataframe(debug_df)

    st.stop()

# =====================================================
# DASHBOARD
# =====================================================
st.title("📊 Performance Dashboard")
st.subheader(f"{selected_month} | {selected_date}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("SHIFT A")
    st.metric("Quantity", metrics["SHIFT_A_QTY"])
    st.metric("Sale Amount", f"₹ {metrics['SHIFT_A_SALE']:,.2f}")
    st.metric("Cash", f"₹ {metrics['SHIFT_A_CASH']:,.2f}")
    st.metric("Paytm", f"₹ {metrics['SHIFT_A_PAYTM']:,.2f}")
    st.metric("ATM", f"₹ {metrics['SHIFT_A_ATM']:,.2f}")
    st.metric("Credit Sale", f"₹ {metrics['SHIFT_A_CREDIT']:,.2f}")
    st.metric("Total Collection", f"₹ {metrics['SHIFT_A_TOTAL']:,.2f}")
    st.metric("Difference", f"₹ {metrics['SHIFT_A_DIFF']:,.2f}")

with col2:
    st.subheader("SHIFT B")
    st.metric("Quantity", metrics["SHIFT_B_QTY"])
    st.metric("Sale Amount", f"₹ {metrics['SHIFT_B_SALE']:,.2f}")
    st.metric("Cash", f"₹ {metrics['SHIFT_B_CASH']:,.2f}")
    st.metric("Paytm", f"₹ {metrics['SHIFT_B_PAYTM']:,.2f}")
    st.metric("ATM", f"₹ {metrics['SHIFT_B_ATM']:,.2f}")
    st.metric("Credit Sale", f"₹ {metrics['SHIFT_B_CREDIT']:,.2f}")
    st.metric("Total Collection", f"₹ {metrics['SHIFT_B_TOTAL']:,.2f}")
    st.metric("Difference", f"₹ {metrics['SHIFT_B_DIFF']:,.2f}")
