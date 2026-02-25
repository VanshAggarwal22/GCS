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
# GOOGLE AUTH (OPTIMIZED)
# =====================================================
@st.cache_resource
def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        service_account_info = dict(st.secrets["gcp_service_account"])
        service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")

        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=scope
        )
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        st.stop()

client = get_gspread_client()

# =====================================================
# LOAD FUNCTIONS (OPTIMIZED)
# =====================================================
@st.cache_data(ttl=600)
def list_spreadsheets():
    try:
        files = client.list_spreadsheet_files()
        return {file["name"]: file["id"] for file in files}
    except Exception:
        return {}

@st.cache_data(ttl=600)
def list_worksheets(spreadsheet_id):
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        return [ws.title for ws in spreadsheet.worksheets()]
    except Exception:
        return []

@st.cache_data(ttl=600)
def load_consolidated(spreadsheet_id, worksheet_name):
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        data = worksheet.get("AA6:AJ14")
    except Exception as e:
        st.error(f"Error loading worksheet {worksheet_name}: {e}")
        return None

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

kpi_data = [
    ("Total Quantity", "QTY", f"{safe_get('QTY'):,.2f}"),
    ("Total Sale", "SALE AMOUNT", f"₹ {safe_get('SALE AMOUNT'):,.2f}"),
    ("Total Cash", "CASH", f"₹ {safe_get('CASH'):,.2f}"),
    ("Total Paytm", "PAYTM", f"₹ {safe_get('PAYTM'):,.2f}"),
    ("Total ATM", "ATM", f"₹ {safe_get('ATM'):,.2f}"),
    ("Total Credit", "CREDIT SALE", f"₹ {safe_get('CREDIT SALE'):,.2f}"),
    ("Total Collection", "TOTAL COLLECTION", f"₹ {safe_get('TOTAL COLLECTION'):,.2f}"),
    ("Difference", "DIFF", f"₹ {safe_get('DIFF'):,.2f}"),
]

for i in range(0, len(kpi_data), 4):
    cols = st.columns(4)
    for j in range(4):
        if i + j < len(kpi_data):
            title, col_name, value = kpi_data[i + j]
            with cols[j]:
                kpi_card(title, value)

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
# 🚨 ALERT PAGE – NEGATIVE DIFFERENCE TRACKER (OPTIMIZED)
# =====================================================
st.divider()
st.title("🚨 Negative Difference Alerts")

@st.cache_data(ttl=3600)  # Cache alert results for 1 hour
def get_all_negative_alerts(spreadsheets_dict):
    alerts = []
    for file_name, file_id in spreadsheets_dict.items():
        try:
            ws_titles = list_worksheets(file_id)
            for title in ws_titles:
                try:
                    sheet_date = pd.to_datetime(title.strip(), dayfirst=True, errors="coerce")
                    if pd.isna(sheet_date):
                        continue

                    # load_consolidated is already cached
                    t_df = load_consolidated(file_id, title)
                    if t_df is not None and "TOTAL" in t_df["SHIFT"].values:
                        t_row = t_df[t_df["SHIFT"] == "TOTAL"].iloc[0]
                        if "DIFF" in t_df.columns:
                            d_val = t_row["DIFF"]
                            if d_val < 0:
                                alerts.append({
                                    "Month File": file_name,
                                    "Date": sheet_date.date(),
                                    "Difference": d_val
                                })
                except Exception:
                    continue
        except Exception:
            continue
    return alerts

with st.expander("🔍 Run Global Scan for Negative Differences", expanded=False):
    st.info("Scanning all spreadsheets for negative 'DIFF' values. This may take a moment...")
    
    alert_results = get_all_negative_alerts(spreadsheets)

    if alert_results:
        alert_df = pd.DataFrame(alert_results).sort_values("Date")
        st.error(f"⚠ {len(alert_results)} Negative differences detected!")

        def highlight_diff(val):
            return "background-color: #7f1d1d; color: white;" if val < -500 else "color: #f87171;" if val < 0 else ""
        
        # Using .map instead of .applymap for future-proofing
        styled_df = alert_df.style.map(highlight_diff, subset=["Difference"])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.success("✅ No negative differences found across all scanned data.")
