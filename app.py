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
# LOAD CONSOLIDATED METRICS FROM FIXED RANGE
# =====================================================
@st.cache_data
def load_consolidated_metrics(spreadsheet_id, worksheet_name):
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)

    # Direct fixed range
    data = worksheet.get("AA7:AI14")

    if not data:
        return {}

    df = pd.DataFrame(data)

    def safe_float(value):
        try:
            return float(str(value).replace(",", "").strip())
        except:
            return 0.0

    try:
        # Based on your layout inside AA7:AI14
        # Index 2 -> SHIFT A
        # Index 4 -> SHIFT B

        shift_a = 2
        shift_b = 4

        metrics = {
            # SHIFT A
            "SHIFT_A_QTY": safe_float(df.iloc[shift_a, 1]),
            "SHIFT_A_SALE": safe_float(df.iloc[shift_a, 2]),
            "SHIFT_A_CASH": safe_float(df.iloc[shift_a, 3]),
            "SHIFT_A_PAYTM": safe_float(df.iloc[shift_a, 4]),
            "SHIFT_A_ATM": safe_float(df.iloc[shift_a, 5]),
            "SHIFT_A_CREDIT": safe_float(df.iloc[shift_a, 6]),
            "SHIFT_A_TOTAL": safe_float(df.iloc[shift_a, 7]),
            "SHIFT_A_DIFF": safe_float(df.iloc[shift_a, 8]),

            # SHIFT B
            "SHIFT_B_QTY": safe_float(df.iloc[shift_b, 1]),
            "SHIFT_B_SALE": safe_float(df.iloc[shift_b, 2]),
            "SHIFT_B_CASH": safe_float(df.iloc[shift_b, 3]),
            "SHIFT_B_PAYTM": safe_float(df.iloc[shift_b, 4]),
            "SHIFT_B_ATM": safe_float(df.iloc[shift_b, 5]),
            "SHIFT_B_CREDIT": safe_float(df.iloc[shift_b, 6]),
            "SHIFT_B_TOTAL": safe_float(df.iloc[shift_b, 7]),
            "SHIFT_B_DIFF": safe_float(df.iloc[shift_b, 8]),
        }

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
    st.error("Could not load AA7:AI14 range. Check sheet structure.")
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
