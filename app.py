import streamlit as st
import pandas as pd

st.set_page_config(page_title="Daily Collection Dashboard", layout="wide")

# -----------------------------
# GOOGLE SHEET CONFIG
# -----------------------------
SHEET_ID = "1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA"
GID = "1671830441"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_csv(CSV_URL, header=2)

    # Normalize column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(" ", "_")
    )

    # -----------------------------
    # DATE COLUMN DETECTION (SAFE)
    # -----------------------------
    possible_date_cols = [
        c for c in df.columns
        if any(k in c for k in ["DATE", "DAY"])
    ]

    if not possible_date_cols:
        st.error(
            f"❌ No DATE column found.\n\nAvailable columns:\n{list(df.columns)}"
        )
        st.stop()

    date_col = possible_date_cols[0]
    df["DATE"] = pd.to_datetime(df[date_col], errors="coerce")

    # -----------------------------
    # SHIFT COLUMN DETECTION
    # -----------------------------
    shift_cols = [c for c in df.columns if "SHIFT" in c]

    if not shift_cols:
        st.error("❌ No SHIFT column found (A / B / C).")
        st.stop()

    df["SHIFT"] = df[shift_cols[0]].astype(str).str.strip()

    # -----------------------------
    # NUMERIC CLEANUP
    # -----------------------------
    for col in df.columns:
        if col not in ["DATE", "SHIFT"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

df = load_data()

# -----------------------------
# COLUMN AUTO-DETECTION
# -----------------------------
def find_col(keyword):
    matches = [c for c in df.columns if keyword in c]
    if not matches:
        st.error(f"❌ Column containing '{keyword}' not found.")
        st.stop()
    return matches[0]

cash_col = find_col("CASH")
rtgs_col = find_col("RTGS")
pid_col = find_col("PID")
total_col = find_col("TOTAL")

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
    options=sorted(df["SHIFT"].unique()),
    default=sorted(df["SHIFT"].unique())
)

filtered_df = df[
    (df["DATE"] >= pd.to_datetime(date_range[0])) &
    (df["DATE"] <= pd.to_datetime(date_range[1])) &
    (df["SHIFT"].isin(selected_shifts))
]

# -----------------------------
# TABS
# -----------------------------
tab1, tab2, tab3 = st.tabs([
    "📊 Daily Overview",
    "🔁 Shift-wise Analysis",
    "📅 Daily Metrics"
])

# ======================================================
# TAB 1 — DAILY OVERVIEW (UNCHANGED LOGIC)
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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Cash", f"₹ {daily[cash_col].sum():,.0f}")
    c2.metric("Total RTGS", f"₹ {daily[rtgs_col].sum():,.0f}")
    c3.metric("Total PID", f"₹ {daily[pid_col].sum():,.0f}")
    c4.metric("Grand Total", f"₹ {daily[total_col].sum():,.0f}")

    st.dataframe(daily, use_container_width=True)

# ======================================================
# TAB 2 — SHIFT-WISE ANALYSIS (FIXED)
# ======================================================
with tab2:
    st.subheader("Shift-wise Analysis")

    shift_daily = (
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

    st.dataframe(shift_daily, use_container_width=True)

    st.markdown("### Overall Shift Totals")

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
# TAB 3 — DAILY METRICS (NEW & ISOLATED)
# ======================================================
with tab3:
    st.subheader("Daily Metrics")

    selected_date = st.selectbox(
        "Select Date",
        sorted(filtered_df["DATE"].dt.date.unique())
    )

    day_df = filtered_df[filtered_df["DATE"].dt.date == selected_date]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash", f"₹ {day_df[cash_col].sum():,.0f}")
    c2.metric("RTGS", f"₹ {day_df[rtgs_col].sum():,.0f}")
    c3.metric("PID", f"₹ {day_df[pid_col].sum():,.0f}")
    c4.metric("Total", f"₹ {day_df[total_col].sum():,.0f}")

    st.markdown("### Shift-wise Breakdown")
    st.dataframe(
        day_df.groupby("SHIFT", as_index=False).agg({
            cash_col: "sum",
            rtgs_col: "sum",
            pid_col: "sum",
            total_col: "sum"
        }),
        use_container_width=True
    )
