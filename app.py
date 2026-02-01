import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------------- CONFIG ----------------
SPREADSHEET_ID = "YOUR_SHEET_ID_HERE"
START_ROW = 7
END_ROW = 14
START_COL = 27  # AA
END_COL = 35    # AI

COLUMNS = [
    "SHIFT",
    "QTY",
    "SALE_AMOUNT",
    "CASH",
    "PAYTM",
    "ATM",
    "CREDIT_SALE",
    "TOTAL_COLLECTION",
    "DIFF"
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

st.set_page_config(page_title="Daily Shift Dashboard", layout="wide")

# ---------------- AUTH ----------------
@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(creds)

# ---------------- DATA LOAD ----------------
@st.cache_data
def load_all_sheets():
    client = get_client()
    sheet = client.open_by_key(SPREADSHEET_ID)

    all_data = []

    for ws in sheet.worksheets():
        values = ws.get_all_values()

        block = values[START_ROW-1:END_ROW]

        for row in block:
            row = row[START_COL-1:END_COL]

            # normalize row length
            if len(row) < len(COLUMNS):
                row += [""] * (len(COLUMNS) - len(row))

            # skip junk rows
            if row[0].strip() == "":
                continue

            record = dict(zip(COLUMNS, row))
            record["DATE"] = ws.title

            all_data.append(record)

    df = pd.DataFrame(all_data)

    # numeric cleanup
    for col in COLUMNS[1:]:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .replace("", "0")
            .astype(float)
        )

    return df

# ---------------- UI ----------------
st.title("📊 Daily Shift Collection Dashboard")

df = load_all_sheets()

dates = sorted(df["DATE"].unique())
selected_date = st.selectbox("Select Date", dates)

day_df = df[df["DATE"] == selected_date]

# ---------------- KPIs ----------------
total = day_df[day_df["SHIFT"] == "TOTAL"].iloc[0]

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Sale Amount", f"₹ {total['SALE_AMOUNT']:,.2f}")
c2.metric("Total Collection", f"₹ {total['TOTAL_COLLECTION']:,.2f}")
c3.metric("Cash", f"₹ {total['CASH']:,.2f}")
c4.metric("Difference", f"₹ {total['DIFF']:,.2f}")

st.divider()

# ---------------- TABLE ----------------
st.subheader("Shift-wise Breakdown")
st.dataframe(
    day_df[day_df["SHIFT"] != "TOTAL"]
    .set_index("SHIFT"),
    use_container_width=True
)

# ---------------- CHARTS ----------------
st.subheader("Collection Distribution")

chart_df = day_df[day_df["SHIFT"] != "TOTAL"].set_index("SHIFT")

st.bar_chart(
    chart_df[["CASH", "PAYTM", "ATM", "CREDIT_SALE"]],
    use_container_width=True
)

st.subheader("Sales vs Collection")
st.line_chart(
    chart_df[["SALE_AMOUNT", "TOTAL_COLLECTION"]],
    use_container_width=True
)
