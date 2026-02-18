import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

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
# LOAD SPREADSHEETS
# =====================================================
@st.cache_data
def list_spreadsheets():
    files = client.list_spreadsheet_files()
    return {file["name"]: file["id"] for file in files}

@st.cache_data
def list_worksheets(spreadsheet_id):
    spreadsheet = client.open_by_key(spreadsheet_id)
    return [ws.title for ws in spreadsheet.worksheets()]

# =====================================================
# LOAD CONSOLIDATED DATA
# =====================================================
@st.cache_data
def load_consolidated(spreadsheet_id, worksheet_name):
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)

    data = worksheet.get("AA6:AJ14")

    if not data:
        return None

    df = pd.DataFrame(data)

    # Row 1 inside range = header
    headers = df.iloc[1]
    df = df[2:]
    df.columns = headers
    df = df.dropna(how="all")

    # Clean numbers
    for col in df.columns[1:]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "")
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.reset_index(drop=True)

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.title("Select Data")

spreadsheets = list_spreadsheets()
selected_month = st.sidebar.selectbox("Select Spreadsheet (Month)", list(spreadsheets.keys()))

spreadsheet_id = spreadsheets[selected_month]
worksheets = list_worksheets(spreadsheet_id)
selected_date = st.sidebar.selectbox("Select Date Sheet", worksheets)

df = load_consolidated(spreadsheet_id, selected_date)

if df is None or df.empty:
    st.error("Could not load data.")
    st.stop()

# =====================================================
# DASHBOARD HEADER
# =====================================================
st.title("📊 Performance Dashboard")
st.subheader(f"{selected_month} | {selected_date}")

# =====================================================
# METRICS SECTION
# =====================================================
total_row = df[df["SHIFT"] == "TOTAL"].iloc[0]

m1, m2, m3, m4 = st.columns(4)

m1.metric("Total Sale", f"₹ {total_row['SALE AMOUNT']:,.2f}")
m2.metric("Total Cash", f"₹ {total_row['CASH']:,.2f}")
m3.metric("Total Paytm", f"₹ {total_row['PAYTM']:,.2f}")
m4.metric("Total Credit", f"₹ {total_row['CREDIT SALE']:,.2f}")

st.divider()

# =====================================================
# SHIFT COMPARISON TABLE
# =====================================================
st.subheader("Shift Performance")
st.dataframe(df, use_container_width=True)

# =====================================================
# GRAPH 1 – SALE AMOUNT BY SHIFT
# =====================================================
st.subheader("Sale Amount by Shift")

shift_df = df[df["SHIFT"] != "TOTAL"]

fig1 = px.bar(
    shift_df,
    x="SHIFT",
    y="SALE AMOUNT",
    text_auto=True,
    color="SHIFT"
)

st.plotly_chart(fig1, use_container_width=True)

# =====================================================
# GRAPH 2 – PAYMENT DISTRIBUTION (TOTAL)
# =====================================================
st.subheader("Payment Distribution (Total)")

payment_data = {
    "Mode": ["Cash", "Paytm", "Credit"],
    "Amount": [
        total_row["CASH"],
        total_row["PAYTM"],
        total_row["CREDIT SALE"]
    ]
}

payment_df = pd.DataFrame(payment_data)

fig2 = px.pie(
    payment_df,
    names="Mode",
    values="Amount",
    hole=0.5
)

st.plotly_chart(fig2, use_container_width=True)
