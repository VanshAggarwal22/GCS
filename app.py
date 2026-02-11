import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================
# PAGE CONFIG
# ==========================
st.set_page_config(
    page_title="Fuel Station Daily Dashboard",
    layout="wide"
)

SHEET_ID = "1_NDdrYnUJnFoJHwc5dZUy5bM920UqMmxP2dUJErGtNA"

# ==========================
# GOOGLE SHEET FETCH
# ==========================
@st.cache_data
def load_sheet(sheet_gid: str) -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={sheet_gid}"
    df = pd.read_csv(url, header=None)
    return df

# ==========================
# HELPERS
# ==========================
def safe_value(df, r, c):
    try:
        return df.iloc[r, c]
    except:
        return None

def section_header(title):
    st.markdown(f"### {title}")

# ==========================
# SESSION STATE STORAGE
# ==========================
if "daily_sheets" not in st.session_state:
    st.session_state.daily_sheets = {}

# ==========================
# SIDEBAR INPUT
# ==========================
st.sidebar.title("📅 Add / Select Daily Sheet")

date_input = st.sidebar.text_input("Enter Date (e.g. 08.01.26)")
gid_input = st.sidebar.text_input("Enter GID for this date")

if st.sidebar.button("➕ Add / Update Date"):
    if date_input and gid_input:
        st.session_state.daily_sheets[date_input] = gid_input
        st.sidebar.success(f"{date_input} added successfully!")

# ==========================
# DATE SELECTION
# ==========================
if len(st.session_state.daily_sheets) == 0:
    st.warning("Please add at least one date and GID from the sidebar.")
    st.stop()

selected_date = st.sidebar.selectbox(
    "Select Available Date",
    list(st.session_state.daily_sheets.keys())
)

selected_gid = st.session_state.daily_sheets[selected_date]

# ==========================
# LOAD DATA
# ==========================
try:
    df = load_sheet(selected_gid)
except:
    st.error("Failed to fetch data. Please check GID.")
    st.stop()

# ==========================
# HEADER
# ==========================
station_name = safe_value(df, 0, 0)

st.title("⛽ Fuel Station Daily Performance Dashboard")
st.caption(f"📍 {station_name} | 📆 {selected_date}")

# ==========================
# KPI CARDS
# ==========================
k1, k2, k3, k4 = st.columns(4)

total_sale = safe_value(df, 5, 5)
total_qty = safe_value(df, 5, 3)
total_collection = safe_value(df, 18, 5)
difference = safe_value(df, 18, 6)

k1.metric("💰 Total Sale (₹)", total_sale)
k2.metric("⚖️ Total Quantity", total_qty)
k3.metric("💵 Total Collection", total_collection)
k4.metric("⚠️ Difference", difference)

st.divider()

# ==========================
# SHIFT SUMMARY
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

col1, col2 = st.columns(2)

with col1:
    st.dataframe(shift_data, use_container_width=True)

with col2:
    fig = px.bar(
        shift_data,
        x="Shift",
        y="Sale",
        text_auto=True,
        title="Shift-wise Sale Distribution"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ==========================
# PAYMENT BREAKDOWN
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

col1, col2 = st.columns(2)

with col1:
    st.dataframe(payment_df, use_container_width=True)

with col2:
    fig = px.pie(
        payment_df,
        names="Mode",
        values="Amount",
        title="Payment Distribution"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ==========================
# DISPENSER ANALYSIS
# ==========================
section_header("⛽ Dispenser-wise Analysis (Shift A Example)")

dispenser_data = []
start_row = 21  # Adjust if needed

for i in range(start_row, start_row + 15):
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

col1, col2 = st.columns(2)

with col1:
    st.dataframe(disp_df, use_container_width=True)

with col2:
    fig = px.line(
        disp_df,
        x="Dispenser",
        y="Quantity",
        markers=True,
        title="Dispenser Consumption"
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ==========================
# RAW DATA VIEW
# ==========================
with st.expander("🔍 View Raw Sheet Data"):
    st.dataframe(df, use_container_width=True)

st.caption("Live data fetched using dynamic GID input • Streamlit Dashboard")
