import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from datetime import datetime

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
def load_sheet(spreadsheet_id, worksheet_name):
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)

    data = worksheet.get("AA6:AJ14")

    if not data:
        return None

    df = pd.DataFrame(data)

    headers = df.iloc[1]
    df = df[2:]
    df.columns = headers
    df = df.dropna(how="all")

    for col in df.columns[1:]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df.reset_index(drop=True)

# =====================================================
# KPI CARD
# =====================================================
def kpi_card(title, value):
    st.markdown(f"""
        <div style="
            background-color:#111827;
            padding:20px;
            border-radius:12px;
            box-shadow:0px 4px 12px rgba(0,0,0,0.2);
        ">
            <div style="color:#9CA3AF;font-size:14px;">{title}</div>
            <div style="color:white;font-size:26px;font-weight:600;">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.title("📅 Select Data")

spreadsheets = list_spreadsheets()
selected_month = st.sidebar.selectbox("Select Month", list(spreadsheets.keys()))
spreadsheet_id = spreadsheets[selected_month]

worksheets = list_worksheets(spreadsheet_id)

# Convert worksheet titles to date safely
date_map = {}
for ws in worksheets:
    try:
        date_obj = datetime.strptime(ws, "%d-%m")
        date_map[date_obj] = ws
    except:
        continue

sorted_dates = sorted(date_map.keys())

# Date Range Picker
selected_range = st.sidebar.date_input(
    "Select Date Range",
    [sorted_dates[0], sorted_dates[-1]]
)

# =====================================================
# CONSOLIDATE RANGE
# =====================================================
combined_df = pd.DataFrame()

if len(selected_range) == 2:
    start_date, end_date = selected_range

    for date_obj in sorted_dates:
        if start_date <= date_obj.date() <= end_date:
            ws_name = date_map[date_obj]
            df = load_sheet(spreadsheet_id, ws_name)

            if df is not None:
                total_row = df[df["SHIFT"] == "TOTAL"]
                if not total_row.empty:
                    combined_df = pd.concat([combined_df, total_row])

# If no range selected fallback
if combined_df.empty:
    st.warning("No data found for selected range.")
    st.stop()

# Group by SHIFT (TOTAL only)
final_df = combined_df.groupby("SHIFT").sum(numeric_only=True).reset_index()
total_row = final_df.iloc[0]

# =====================================================
# DASHBOARD HEADER
# =====================================================
st.title("📊 Performance Dashboard")
st.subheader(f"{selected_month}")

# =====================================================
# KPI SECTION
# =====================================================
col1, col2, col3, col4 = st.columns(4)
col5, col6, col7, col8 = st.columns(4)

def safe_get(column):
    return float(total_row[column]) if column in final_df.columns else 0

with col1:
    kpi_card("Total Quantity", f"{safe_get('QTY'):,.2f}")
with col2:
    kpi_card("Total Sale", f"₹ {safe_get('SALE AMOUNT'):,.2f}")
with col3:
    kpi_card("Total Cash", f"₹ {safe_get('CASH'):,.2f}")
with col4:
    kpi_card("Total Paytm", f"₹ {safe_get('PAYTM'):,.2f}")

with col5:
    kpi_card("Total ATM", f"₹ {safe_get('ATM'):,.2f}")
with col6:
    kpi_card("Total Credit", f"₹ {safe_get('CREDIT SALE'):,.2f}")
with col7:
    kpi_card("Total Collection", f"₹ {safe_get('TOTAL COLLECTION'):,.2f}")
with col8:
    kpi_card("Difference", f"₹ {safe_get('DIFF'):,.2f}")

st.divider()

# =====================================================
# GRAPH – PAYMENT DISTRIBUTION
# =====================================================
payment_df = pd.DataFrame({
    "Mode": ["Cash", "Paytm", "ATM", "Credit"],
    "Amount": [
        safe_get("CASH"),
        safe_get("PAYTM"),
        safe_get("ATM"),
        safe_get("CREDIT SALE")
    ]
})

fig1 = px.pie(payment_df, names="Mode", values="Amount", hole=0.5)
st.plotly_chart(fig1, use_container_width=True)

# =====================================================
# MONTH WISE ANALYSIS
# =====================================================
st.subheader("📈 Month-wise Daily Trend")

trend_data = []

for date_obj in sorted_dates:
    ws_name = date_map[date_obj]
    df = load_sheet(spreadsheet_id, ws_name)

    if df is not None:
        total_row = df[df["SHIFT"] == "TOTAL"]
        if not total_row.empty:
            trend_data.append({
                "Date": date_obj.strftime("%d-%m"),
                "Sale": float(total_row["SALE AMOUNT"])
            })

trend_df = pd.DataFrame(trend_data)

if not trend_df.empty:
    fig_month = px.line(
        trend_df,
        x="Date",
        y="Sale",
        markers=True
    )
    st.plotly_chart(fig_month, use_container_width=True)
