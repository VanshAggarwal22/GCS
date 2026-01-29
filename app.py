import streamlit as st
import pandas as pd

st.set_page_config(page_title="Daily Collection Dashboard", layout="wide")

# -----------------------------
# GOOGLE SHEET CONFIG
# -----------------------------
SHEET_ID = "1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA"
GID = "1671830441"

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL, header=2)

    # Clean column names
    df.columns = (
        df.columns.str.strip()
        .str.upper()
        .str.replace(" ", "_")
    )

    # Detect DATE column
    date_col = [c for c in df.columns if "DATE" in c][0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df.rename(columns={date_col: "DATE"}, inplace=True)

    # Detect SHIFT column
    shift_col = [c for c in df.columns if "SHIFT" in c][0]
    df.rename(columns={shift_col: "SHIFT"}, inplace=True)

    # Numeric cleanup
    for col in df.columns:
        if col not in ["DATE", "SHIFT"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

df = load_data()

# -----------------------------
# SIDEBAR FILTERS
# -----------------------------
st.sidebar.title("Filters")

min_date = df["DATE"].min()
max_date = df["DATE"].max()

date_range = st.sidebar.date_input(
    "Select Date Range",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

selected_shifts = st.sidebar.multiselect(
    "Select Shifts",
    options=sorted(df["SHIFT"].dropna().unique()),
    default=sorted(df["SHIFT"].dropna().unique())
)

filtered_df = df[
    (df["DATE"] >= pd.to_datetime(date_range[0])) &
    (df["DATE"] <= pd.to_datetime(date_range[1])) &
    (df["SHIFT"].isin(selected_shifts))
]

# -----------------------------
# COLUMN AUTO-DETECTION
# -----------------------------
cash_col = [c for c in df.columns if "CASH" in c][0]
rtgs_col = [c for c in df.columns if "RTGS" in c][0]
pid_col = [c for c in df.columns if "PID" in c][0]
total_col = [c for c in df.columns if "TOTAL" in c][0]

# -----------------------------
# TABS
# -----------------------------
tab1, tab2, tab3 = st.tabs([
    "📊 Daily Overview",
    "🔁 Shift-wise Analysis",
    "📅 Daily Metrics"
])

# ======================================================
# TAB 1 — DAILY OVERVIEW (KEEP SIMPLE & CORRECT)
# ======================================================
with tab1:
    st.subheader("Daily Overview")

    daily = (
        filtered_df
        .groupby("DATE", as_index=False)
        .agg({
            cash_col: "sum",
            rtgs_col: "sum",
            pid_col: "sum",
            total_col: "sum"
        })
        .sort_values("DATE")
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Cash", f"₹ {daily[cash_col].sum():,.0f}")
    col2.metric("Total RTGS", f"₹ {daily[rtgs_col].sum():,.0f}")
    col3.metric("Total PID", f"₹ {daily[pid_col].sum():,.0f}")
    col4.metric("Grand Total", f"₹ {daily[total_col].sum():,.0f}")

    st.dataframe(daily, use_container_width=True)

# ======================================================
# TAB 2 — SHIFT-WISE ANALYSIS (FIXED PROPERLY)
# ======================================================
with tab2:
    st.subheader("Shift-wise Analysis")

    shift_summary = (
        filtered_df
        .groupby(["DATE", "SHIFT"], as_index=False)
        .agg({
            cash_col: "sum",
            rtgs_col: "sum",
            pid_col: "sum",
            total_col: "sum"
        })
        .sort_values(["DATE", "SHIFT"])
    )

    st.dataframe(shift_summary, use_container_width=True)

    st.markdown("### Shift Totals (Overall)")

    shift_totals = (
        filtered_df
        .groupby("SHIFT", as_index=False)
        .agg({
            cash_col: "sum",
            rtgs_col: "sum",
            pid_col: "sum",
            total_col: "sum"
        })
    )

    st.dataframe(shift_totals, use_container_width=True)

# ======================================================
# TAB 3 — DAILY METRICS (NEW, SEPARATE, SAFE)
# ======================================================
with tab3:
    st.subheader("Daily Metrics Explorer")

    selected_date = st.selectbox(
        "Select Date",
        options=sorted(filtered_df["DATE"].dt.date.unique())
    )

    day_df = filtered_df[filtered_df["DATE"].dt.date == selected_date]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Cash", f"₹ {day_df[cash_col].sum():,.0f}")
    c2.metric("RTGS", f"₹ {day_df[rtgs_col].sum():,.0f}")
    c3.metric("PID", f"₹ {day_df[pid_col].sum():,.0f}")
    c4.metric("Total", f"₹ {day_df[total_col].sum():,.0f}")

    st.markdown("### Shift Breakdown (Selected Date)")
    st.dataframe(
        day_df.groupby("SHIFT", as_index=False).agg({
            cash_col: "sum",
            rtgs_col: "sum",
            pid_col: "sum",
            total_col: "sum"
        }),
        use_container_width=True
    )
