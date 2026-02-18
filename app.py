import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Performance Dashboard", layout="wide")

# =====================================================
# GOOGLE AUTH (FROM STREAMLIT SECRETS)
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
# LIST SPREADSHEETS (MONTHS)
# =====================================================
@st.cache_data
def list_spreadsheets():
    files = client.list_spreadsheet_files()
    return {file["name"]: file["id"] for file in files}

# =====================================================
# LIST WORKSHEETS (DATES)
# =====================================================
@st.cache_data
def list_worksheets(spreadsheet_id):
    spreadsheet = client.open_by_key(spreadsheet_id)
    return [ws.title for ws in spreadsheet.worksheets()]

# =====================================================
# LOAD CONSOLIDATE DATA BLOCK
# =====================================================
@st.cache_data
def load_consolidated_metrics(spreadsheet_id, worksheet_name):
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)

    raw = worksheet.get_all_values()

    if not raw:
        return {}

    df = pd.DataFrame(raw)

    consolidate_row = None
    consolidate_col = None

    # Locate "CONSOLIDATE DATA"
    for r in range(len(df)):
        for c in range(len(df.columns)):
            if str(df.iloc[r, c]).strip().upper() == "CONSOLIDATE DATA":
                consolidate_row = r
                consolidate_col = c
                break
        if consolidate_row is not None:
            break

    if consolidate_row is None:
        return {}

    def safe_float(value):
        try:
            return float(str(value).replace(",", ""))
        except:
            return 0.0

    metrics = {}

    try:
        # SHIFT A
        metrics["SHIFT_A_QTY"] = safe_float(df.iloc[consolidate_row+2, consolidate_col+1])
        metrics["SHIFT_A_SALE"] = safe_float(df.iloc[consolidate_row+2, consolidate_col+2])
        metrics["SHIFT_A_CASH"] = safe_float(df.iloc[consolidate_row+2, consolidate_col+3])
        metrics["SHIFT_A_PAYTM"] = safe_float(df.iloc[consolidate_row+2, consolidate_col+4])
        metrics["SHIFT_A_ATM"] = safe_float(df.iloc[consolidate_row+2, consolidate_col+5])
        metrics["SHIFT_A_CREDIT"] = safe_float(df.iloc[consolidate_row+2, consolidate_col+6])
        metrics["SHIFT_A_TOTAL"] = safe_float(df.iloc[consolidate_row+2, consolidate_col+7])
        metrics["SHIFT_A_DIFF"] = safe_float(df.iloc[consolidate_row+2, consolidate_col+8])

        # SHIFT B
        metrics["SHIFT_B_QTY"] = safe_float(df.iloc[consolidate_row+4, consolidate_col+1])
        metrics["SHIFT_B_SALE"] = safe_float(df.iloc[consolidate_row+4, consolidate_col+2])
        metrics["SHIFT_B_CASH"] = safe_float(df.iloc[consolidate_row+4, consolidate_col+3])
        metrics["SHIFT_B_PAYTM"] = safe_float(df.iloc[consolidate_row+4, consolidate_col+4])
        metrics["SHIFT_B_ATM"] = safe_float(df.iloc[consolidate_row+4, consolidate_col+5])
        metrics["SHIFT_B_CREDIT"] = safe_float(df.iloc[consolidate_row+4, consolidate_col+6])
        metrics["SHIFT_B_TOTAL"] = safe_float(df.iloc[consolidate_row+4, consolidate_col+7])
        metrics["SHIFT_B_DIFF"] = safe_float(df.iloc[consolidate_row+4, consolidate_col+8])

    except:
        return {}

    return metrics

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
# LOAD METRICS
# =====================================================
metrics = load_consolidated_metrics(spreadsheet_id, selected_date)

if not metrics:
    st.error("Could not extract CONSOLIDATE DATA section.")
    st.stop()

# =====================================================
# DASHBOARD UI
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
