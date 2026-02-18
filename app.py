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

    # Pull Consolidated Section
    data = worksheet.get("AA6:AJ14")

    if not data:
        return None

    df = pd.DataFrame(data)

    # Row 1 inside range = header
    headers = df.iloc[1]
    df = df.iloc[2:]
    df.columns = headers

    # Clean column names
    df.columns = df.columns.str.strip()

    df = df.dropna(how="all")

    # Clean numeric columns
    for col in df.columns[1:]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df.reset_index(drop=True)

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.title("📁 Select Data")

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
# METRICS SECTION (ALL TOTALS)
# =====================================================
if "TOTAL" not in df["SHIFT"].values:
    st.error("TOTAL row not found.")
    st.stop()

total_row = df[df["SHIFT"] == "TOTAL"].iloc[0]

st.subheader("🔢 Overall Performance")

row1 = st.columns(4)
row2 = st.columns(4)

# Row 1
row1[0].metric("Total Quantity", f"{total_row['QTY']:,.2f}")
row1[1].metric("Total Sale", f"₹ {total_row['SALE AMOUNT']:,.2f}")
row1[2].metric("Total Cash", f"₹ {total_row['CASH']:,.2f}")
row1[3].metric("Total Paytm", f"₹ {total_row['PAYTM']:,.2f}")

# Row 2
row2[0].metric("Total ATM", f"₹ {total_row['ATM']:,.2f}")
row2[1].metric("Total Credit", f"₹ {total_row['CREDIT SALE']:,.2f}")
row2[2].metric("Total Collection", f"₹ {total_row['TOTAL COLLECTION']:,.2f}")

diff_value = total_row["DIFF"]

row2[3].metric(
    "Difference",
    f"₹ {diff_value:,.2f}",
    delta=f"{diff_value:,.2f}"
)

st.divider()

# =====================================================
# SHIFT TABLE
# =====================================================
st.subheader("📋 Shift Performance")

st.dataframe(
    df.style.format({
        "QTY": "{:,.2f}",
        "SALE AMOUNT": "{:,.2f}",
        "CASH": "{:,.2f}",
        "PAYTM": "{:,.2f}",
        "ATM": "{:,.2f}",
        "CREDIT SALE": "{:,.2f}",
        "TOTAL COLLECTION": "{:,.2f}",
        "DIFF": "{:,.2f}",
    }),
    use_container_width=True
)

# =====================================================
# GRAPH 1 – SALE AMOUNT BY SHIFT
# =====================================================
st.subheader("📊 Sale Amount by Shift")

shift_df = df[df["SHIFT"] != "TOTAL"]

fig1 = px.bar(
    shift_df,
    x="SHIFT",
    y="SALE AMOUNT",
    text_auto=True,
    color="SHIFT"
)

fig1.update_layout(height=400)

st.plotly_chart(fig1, use_container_width=True)

# =====================================================
# GRAPH 2 – PAYMENT DISTRIBUTION (TOTAL)
# =====================================================
st.subheader("💳 Payment Distribution (Total)")

payment_data = {
    "Mode": ["Cash", "Paytm", "ATM", "Credit"],
    "Amount": [
        total_row["CASH"],
        total_row["PAYTM"],
        total_row["ATM"],
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

fig2.update_layout(height=400)

st.plotly_chart(fig2, use_container_width=True)
