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
# CUSTOM KPI STYLING
# =====================================================
st.markdown("""
<style>
.kpi-card {
    background: linear-gradient(135deg, #1f2937, #111827);
    padding: 20px;
    border-radius: 18px;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.15);
    text-align: center;
}
.kpi-title {
    font-size: 14px;
    color: #9ca3af;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 26px;
    font-weight: bold;
    color: white;
}
</style>
""", unsafe_allow_html=True)

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
# PROFESSIONAL KPI CARDS
# =====================================================
st.subheader("🔢 Overall Performance")

row1 = st.columns(4)
row2 = st.columns(4)

def kpi_card(title, value):
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

with row1[0]:
    kpi_card("Total Quantity", f"{total_row['QTY']:,.2f}")

with row1[1]:
    kpi_card("Total Sale", f"₹ {total_row['SALE AMOUNT']:,.2f}")

with row1[2]:
    kpi_card("Total Cash", f"₹ {total_row['CASH']:,.2f}")

with row1[3]:
    kpi_card("Total Paytm", f"₹ {total_row['PAYTM']:,.2f}")

with row2[0]:
    kpi_card("Total ATM", f"₹ {total_row['ATM']:,.2f}")

with row2[1]:
    kpi_card("Total Credit", f"₹ {total_row['CREDIT SALE']:,.2f}")

with row2[2]:
    kpi_card("Total Collection", f"₹ {total_row['TOTAL COLLECTION']:,.2f}")

with row2[3]:
    kpi_card("Difference", f"₹ {total_row['DIFF']:,.2f}")

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
