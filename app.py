import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Google Sheets Dashboard", layout="wide")

# -----------------------------
# GOOGLE CONNECTION
# -----------------------------
@st.cache_resource
def connect_google():

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    service_account_info = dict(st.secrets["gcp_service_account"])

    # Convert \n to real newlines
    service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=scope
    )

    client = gspread.authorize(credentials)
    return client


client = connect_google()

# -----------------------------
# FETCH ALL SPREADSHEETS
# -----------------------------
@st.cache_data(ttl=300)
def get_spreadsheets():
    return client.list_spreadsheet_files()


files = get_spreadsheets()

if not files:
    st.error("No spreadsheets found. Share sheet with service account email.")
    st.stop()

file_names = [file["name"] for file in files]

selected_file = st.sidebar.selectbox("Select Spreadsheet (Month)", file_names)

file_id = next(file["id"] for file in files if file["name"] == selected_file)

spreadsheet = client.open_by_key(file_id)

# -----------------------------
# FETCH WORKSHEETS (DATES)
# -----------------------------
worksheets = spreadsheet.worksheets()
worksheet_names = [ws.title for ws in worksheets]

selected_sheet = st.sidebar.selectbox("Select Date Sheet", worksheet_names)

worksheet = spreadsheet.worksheet(selected_sheet)

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data(ttl=300)
def load_data(ws):
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    return df


df = load_data(worksheet)

if df.empty:
    st.warning("No data found in this sheet.")
    st.stop()

st.title("📊 Google Sheets Live Dashboard")

st.subheader(f"Spreadsheet: {selected_file}")
st.subheader(f"Sheet: {selected_sheet}")

# -----------------------------
# CLEAN NUMERIC DATA
# -----------------------------
for col in df.columns:
    df[col] = pd.to_numeric(df[col], errors="ignore")

numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns

# -----------------------------
# METRICS SECTION
# -----------------------------
st.markdown("## 🔢 Key Metrics")

cols = st.columns(min(len(numeric_cols), 4))

for i, col in enumerate(numeric_cols[:4]):
    cols[i].metric(
        label=col,
        value=round(df[col].sum(), 2)
    )

# -----------------------------
# DATA TABLE
# -----------------------------
st.markdown("## 📄 Data Table")
st.dataframe(df, use_container_width=True)

# -----------------------------
# CHARTS
# -----------------------------
st.markdown("## 📈 Visualizations")

if len(numeric_cols) > 0:
    selected_chart_col = st.selectbox("Select Column for Chart", numeric_cols)

    st.line_chart(df[selected_chart_col])
else:
    st.info("No numeric columns available for charts.")
