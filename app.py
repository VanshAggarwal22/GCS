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
# LOAD FUNCTIONS (UNCHANGED)
# =====================================================
@st.cache_data
def list_spreadsheets():
    files = client.list_spreadsheet_files()
    return {file["name"]: file["id"] for file in files}

@st.cache_data
def list_worksheets(spreadsheet_id):
    spreadsheet = client.open_by_key(spreadsheet_id)
    return [ws.title for ws in spreadsheet.worksheets()]

@st.cache_data
def load_consolidated(spreadsheet_id, worksheet_name):
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)

    data = worksheet.get("AA6:AJ14")

    if not data:
        return None

    df = pd.DataFrame(data)

    headers = df.iloc[1]
    df = df.iloc[2:]
    df.columns = headers
    df.columns = df.columns.str.strip()
    df = df.dropna(how="all")

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

st.sidebar.markdown("### 📅 Date Range Selection")
date_range = st.sidebar.date_input("Select Date Range", [])

# =====================================================
# ENTERPRISE CONSOLIDATION LOGIC
# =====================================================
def get_dashboard_df(date_range, selected_month, selected_date):

    # ✅ If date range selected → scan ALL spreadsheets
    if len(date_range) == 2:

        start_date, end_date = date_range
        all_data = []

        for file_name, file_id in spreadsheets.items():

            try:
                ws_list = list_worksheets(file_id)

                for sheet in ws_list:
                    try:
                        sheet_date = pd.to_datetime(
                            sheet.strip(),
                            dayfirst=True,
                            errors="coerce"
                        )

                        if pd.notna(sheet_date):
                            if start_date <= sheet_date.date() <= end_date:

                                temp_df = load_consolidated(file_id, sheet)

                                if temp_df is not None:
                                    all_data.append(temp_df)

                    except:
                        continue

            except:
                continue

        if all_data:
            combined = pd.concat(all_data)

            consolidated = (
                combined.groupby("SHIFT")
                .sum(numeric_only=True)
                .reset_index()
            )

            return consolidated

        return None

    # ✅ If no date range → normal single sheet behavior
    return load_consolidated(spreadsheet_id, selected_date)


# Get main dataframe
df = get_dashboard_df(date_range, selected_month, selected_date)

if df is None or df.empty:
    st.error("No data available for selection.")
    st.stop()

# =====================================================
# HEADER
# =====================================================
st.title("📊 Performance Dashboard")

if len(date_range) == 2:
    st.subheader("Consolidated View (All Spreadsheets)")
else:
    st.subheader(f"{selected_month} | {selected_date}")

# =====================================================
# KPI SECTION
# =====================================================
if "TOTAL" not in df["SHIFT"].values:
    st.error("TOTAL row not found.")
    st.stop()

total_row = df[df["SHIFT"] == "TOTAL"].iloc[0]

def safe_get(column):
    return total_row[column] if column in df.columns else 0

def kpi_card(title, value):
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
        </div>
    """, unsafe_allow_html=True)

st.subheader("🔢 Overall Performance")

row1 = st.columns(4)
row2 = st.columns(4)

with row1[0]:
    kpi_card("Total Quantity", f"{safe_get('QTY'):,.2f}")

with row1[1]:
    kpi_card("Total Sale", f"₹ {safe_get('SALE AMOUNT'):,.2f}")

with row1[2]:
    kpi_card("Total Cash", f"₹ {safe_get('CASH'):,.2f}")

with row1[3]:
    kpi_card("Total Paytm", f"₹ {safe_get('PAYTM'):,.2f}")

with row2[0]:
    kpi_card("Total ATM", f"₹ {safe_get('ATM'):,.2f}")

with row2[1]:
    kpi_card("Total Credit", f"₹ {safe_get('CREDIT SALE'):,.2f}")

with row2[2]:
    kpi_card("Total Collection", f"₹ {safe_get('TOTAL COLLECTION'):,.2f}")

with row2[3]:
    kpi_card("Difference", f"₹ {safe_get('DIFF'):,.2f}")

st.divider()

# =====================================================
# SHIFT TABLE
# =====================================================
st.subheader("📋 Shift Performance")
st.dataframe(df, use_container_width=True)

# =====================================================
# SALE BY SHIFT
# =====================================================
st.subheader("📊 Sale Amount by Shift")

shift_df = df[df["SHIFT"] != "TOTAL"]

if "SALE AMOUNT" in df.columns:
    fig1 = px.bar(
        shift_df,
        x="SHIFT",
        y="SALE AMOUNT",
        text_auto=True,
        color="SHIFT"
    )
    st.plotly_chart(fig1, use_container_width=True)

# =====================================================
# PAYMENT DISTRIBUTION
# =====================================================
st.subheader("💳 Payment Distribution (Total)")

payment_modes = ["CASH", "PAYTM", "ATM", "CREDIT SALE"]

payment_data = {
    "Mode": [],
    "Amount": []
}

for mode in payment_modes:
    if mode in df.columns:
        payment_data["Mode"].append(mode.title())
        payment_data["Amount"].append(safe_get(mode))

payment_df = pd.DataFrame(payment_data)

if not payment_df.empty:
    fig2 = px.pie(
        payment_df,
        names="Mode",
        values="Amount",
        hole=0.5
    )
    st.plotly_chart(fig2, use_container_width=True)

# =====================================================
# 🚨 ALERT PAGE – NEGATIVE DIFFERENCE TRACKER
# =====================================================
st.divider()
st.title("🚨 Negative Difference Alerts")

alert_data = []

for file_name, file_id in spreadsheets.items():
    try:
        ws_list = list_worksheets(file_id)

        for sheet in ws_list:
            try:
                sheet_date = pd.to_datetime(
                    sheet.strip(),
                    dayfirst=True,
                    errors="coerce"
                )

                if pd.notna(sheet_date):

                    temp_df = load_consolidated(file_id, sheet)

                    if temp_df is not None and "TOTAL" in temp_df["SHIFT"].values:

                        total_row = temp_df[temp_df["SHIFT"] == "TOTAL"].iloc[0]

                        if "DIFF" in temp_df.columns:
                            diff_value = total_row["DIFF"]

                            if diff_value < 0:
                                alert_data.append({
                                    "Month File": file_name,
                                    "Date": sheet_date.date(),
                                    "Difference": diff_value
                                })

            except:
                continue

    except:
        continue


if alert_data:
    alert_df = pd.DataFrame(alert_data).sort_values("Date")

    st.error("⚠ Negative differences detected!")

    # Highlight rows where Difference < -500
    def highlight_diff(val):
        if val < -500:
            return "background-color: #7f1d1d; color: white;"
        return ""
    
    styled_df = alert_df.style.applymap(
        highlight_diff,
        subset=["Difference"]
    )

st.dataframe(styled_df, use_container_width=True)
else:
    st.success("✅ No negative differences found across all data.")
