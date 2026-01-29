import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================
# CONFIG
# ==========================
st.set_page_config(
    page_title="Fuel Station Daily Dashboard",
    layout="wide"
)

SHEET_ID = "1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA"

# ==========================
# GOOGLE SHEET FETCH
# ==========================
@st.cache_data
def load_sheet(sheet_name: str) -> pd.DataFrame:
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
        f"/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    )
    return pd.read_csv(url, header=None)

# ==========================
# HELPERS
# ==========================
def safe_value(df, r, c):
    try:
        return df.iloc[r, c]
    except:
        return None

def section_header(title):
    st.markdown(f"""
    <div style="padding:10px 0px">
        <h3>{title}</h3>
    </div>
    """, unsafe_allow_html=True)

# ==========================
# SIDEBAR
# ==========================
st.sidebar.title("📅 Select Date (Sheet)")

# Sheet names must match Google Sheet tabs exactly
sheet_names = [
    "01.01.26", "02.01.26", "03.01.26", "04.01.26",
    "05.01.26", "06.01.26", "07.01.26"
]

selected_sheet = st.sidebar.selectbox(
    "Available Dates",
    sheet_names
)

df = load_sheet(selected_sheet)

# ==========================
# HEADER INFO (EDIT ROW/COLUMN IF NEEDED)
# ==========================
station_name = safe_value(df, 0, 0)
date_value = selected_sheet

st.title("⛽ Fuel Station Daily Performance Dashboard")
st.caption(f"📍 {station_name} | 📆 {date_value}")

# ==========================
# KPI CARDS
# ==========================
k1, k2, k3, k4 = st.columns(4)

total_sale = safe_value(df, 5, 5)
total_qty = safe_value(df, 5, 3)
total_collection = safe_value(df, 18, 5)
difference = safe_value(df, 18, 6)

k1.metric("💰 Total Sale (₹)", total_sale)
k2.metric("⚖️ Total Quantity (Kg)", total_qty)
k3.metric("💵 Total Collection", total_collection)
k4.metric("⚠️ Difference", difference)

st.divider()

# ==========================
# SHIFT-WISE SUMMARY
# ==========================
section_header("🕒 Shift-wise Summary")

shift_data = pd.DataFrame({
    "Shift": ["A", "B", "C"],
    "Quantity": [
        safe_value(df, 7, 3),
        safe_value(df, 10, 3),
        safe_value(df, 13, 3)
    ],
    "Sale": [
        safe_value(df, 7, 5),
        safe_value(df, 10, 5),
        safe_value(df, 13, 5)
    ],
    "Difference": [
        safe_value(df, 7, 6),
        safe_value(df, 10, 6),
        safe_value(df, 13, 6)
    ]
})

c1, c2 = st.columns(2)

with c1:
    st.dataframe(shift_data, use_container_width=True)

with c2:
    fig = px.bar(
        shift_data,
        x="Shift",
        y="Sale",
        title="Shift-wise Sale Distribution",
        text_auto=True
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ==========================
# PAYMENT MODE BREAKUP
# ==========================
section_header("💳 Payment Mode Breakdown")

payment_df = pd.DataFrame({
    "Mode": ["Cash", "Paytm", "ATM", "Credit"],
    "Amount": [
        safe_value(df, 16, 5),
        safe_value(df, 15, 5),
        safe_value(df, 14, 5),
        safe_value(df, 17, 5)
    ]
})

c1, c2 = st.columns(2)

with c1:
    st.dataframe(payment_df, use_container_width=True)

with c2:
    fig = px.pie(
        payment_df,
        names="Mode",
        values="Amount",
        title="Payment Mode Contribution"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ==========================
# DISPENSER-WISE ANALYSIS
# ==========================
section_header("⛽ Dispenser-wise Analysis (Shift A Example)")

dispenser_data = []

start_row = 21  # CHANGE if layout differs
for i in range(start_row, start_row + 10):
    if pd.isna(safe_value(df, i, 0)):
        break
    dispenser_data.append({
        "Dispenser": safe_value(df, i, 0),
        "Opening": safe_value(df, i, 1),
        "Closing": safe_value(df, i, 2),
        "Quantity": safe_value(df, i, 3),
        "Sale": safe_value(df, i, 5)
    })

disp_df = pd.DataFrame(dispenser_data)

c1, c2 = st.columns(2)

with c1:
    st.dataframe(disp_df, use_container_width=True)

with c2:
    fig = px.line(
        disp_df,
        x="Dispenser",
        y="Quantity",
        markers=True,
        title="Dispenser Consumption Trend"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ==========================
# RAW DATA (FOR VERIFICATION)
# ==========================
with st.expander("🔍 View Raw Sheet Data"):
    st.dataframe(df, use_container_width=True)

st.caption("Live data fetched directly from Google Sheets • Streamlit Dashboard")
