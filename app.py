import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Daily Operations Dashboard", layout="wide")

# =====================================================
# GOOGLE SHEET CONFIG
# =====================================================
SHEET_ID = "1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA"
GID = "1671830441"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =====================================================
# HELPER: DEDUPLICATE COLUMN NAMES (PANDAS 2 SAFE)
# =====================================================
def dedup_columns(cols):
    seen = {}
    new_cols = []
    for c in cols:
        if c not in seen:
            seen[c] = 0
            new_cols.append(c)
        else:
            seen[c] += 1
            new_cols.append(f"{c}_{seen[c]}")
    return new_cols

# =====================================================
# LOAD & CLEAN DATA (AUTO HEADER + DATE DETECTION)
# =====================================================
@st.cache_data(show_spinner=False)
def load_data():
    raw = pd.read_csv(CSV_URL, header=None)

    # 🔍 Auto-detect header row (row containing DATE / DAY)
    header_row = None
    for i in range(len(raw)):
        row_vals = raw.iloc[i].astype(str).str.upper().tolist()
        if any("DATE" in v or "DAY" in v for v in row_vals):
            header_row = i
            break

    if header_row is None:
        st.error("❌ Could not auto-detect header row containing DATE")
        st.stop()

    # Set header
    raw.columns = raw.iloc[header_row]
    df = raw.iloc[header_row + 1:].copy()

    # Normalize column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(" ", "_")
    )

    # Deduplicate column names (SAFE)
    df.columns = dedup_columns(df.columns)

    # Drop empty rows
    df = df.dropna(how="all")

    # -----------------------------
    # DATE COLUMN (1st column)
    # -----------------------------
    df["DATE"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")

    # -----------------------------
    # SHIFT COLUMN (2nd column)
    # -----------------------------
    df["SHIFT"] = df.iloc[:, 1].astype(str).str.strip()

    # -----------------------------
    # NUMERIC COLUMNS
    # -----------------------------
    for col in df.columns[2:]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Remove invalid dates
    df = df.dropna(subset=["DATE"])

    return df


df = load_data()

# =====================================================
# COLUMN AUTO-DETECTION
# =====================================================
def find_col(keyword):
    for c in df.columns:
        if keyword in c:
            return c
    st.error(f"❌ Column containing '{keyword}' not found")
    st.stop()

CASH_COL = find_col("CASH")
RTGS_COL = find_col("RTGS")
PID_COL = find_col("PID")
TOTAL_COL = find_col("TOTAL")

DISP_COLS = [c for c in df.columns if "DISP" in c]

# =====================================================
# SIDEBAR FILTERS
# =====================================================
st.sidebar.title("Filters")

min_date = df["DATE"].min()
max_date = df["DATE"].max()

date_range = st.sidebar.date_input(
    "Select Date Range",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

shift_options = sorted(df["SHIFT"].dropna().unique())

selected_shifts = st.sidebar.multiselect(
    "Select Shifts",
    options=shift_options,
    default=shift_options
)

filtered_df = df[
    (df["DATE"] >= pd.to_datetime(date_range[0])) &
    (df["DATE"] <= pd.to_datetime(date_range[1])) &
    (df["SHIFT"].isin(selected_shifts))
]

# =====================================================
# TABS
# =====================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Daily Overview",
    "🔁 Shift-wise Analysis",
    "📅 Daily Metrics",
    "⛽ Dispenser Trend"
])

# =====================================================
# TAB 1 — DAILY OVERVIEW (UNCHANGED)
# =====================================================
with tab1:
    st.subheader("Daily Overview")

    daily = (
        filtered_df
        .groupby("DATE", as_index=False)
        .agg({
            CASH_COL: "sum",
            RTGS_COL: "sum",
            PID_COL: "sum",
            TOTAL_COL: "sum"
        })
        .sort_values("DATE")
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Cash", f"₹ {daily[CASH_COL].sum():,.0f}")
    c2.metric("Total RTGS", f"₹ {daily[RTGS_COL].sum():,.0f}")
    c3.metric("Total PID", f"₹ {daily[PID_COL].sum():,.0f}")
    c4.metric("Grand Total", f"₹ {daily[TOTAL_COL].sum():,.0f}")

    st.dataframe(daily, use_container_width=True)

# =====================================================
# TAB 2 — SHIFT-WISE ANALYSIS
# =====================================================
with tab2:
    st.subheader("Shift-wise Analysis")

    shift_daily = (
        filtered_df
        .groupby(["DATE", "SHIFT"], as_index=False)
        .agg({
            CASH_COL: "sum",
            RTGS_COL: "sum",
            PID_COL: "sum",
            TOTAL_COL: "sum"
        })
        .sort_values(["DATE", "SHIFT"])
    )

    st.dataframe(shift_daily, use_container_width=True)

    st.markdown("### Overall Shift Totals")

    shift_totals = (
        filtered_df
        .groupby("SHIFT", as_index=False)
        .agg({
            CASH_COL: "sum",
            RTGS_COL: "sum",
            PID_COL: "sum",
            TOTAL_COL: "sum"
        })
    )

    st.dataframe(shift_totals, use_container_width=True)

# =====================================================
# TAB 3 — DAILY METRICS
# =====================================================
with tab3:
    st.subheader("Daily Metrics")

    selected_date = st.selectbox(
        "Select Date",
        sorted(filtered_df["DATE"].dt.date.unique())
    )

    day_df = filtered_df[filtered_df["DATE"].dt.date == selected_date]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash", f"₹ {day_df[CASH_COL].sum():,.0f}")
    c2.metric("RTGS", f"₹ {day_df[RTGS_COL].sum():,.0f}")
    c3.metric("PID", f"₹ {day_df[PID_COL].sum():,.0f}")
    c4.metric("Total", f"₹ {day_df[TOTAL_COL].sum():,.0f}")

    st.dataframe(
        day_df.groupby("SHIFT", as_index=False).agg({
            CASH_COL: "sum",
            RTGS_COL: "sum",
            PID_COL: "sum",
            TOTAL_COL: "sum"
        }),
        use_container_width=True
    )

# =====================================================
# TAB 4 — DISPENSER TREND
# =====================================================
with tab4:
    st.subheader("Dispenser Consumption Trend")

    if not DISP_COLS:
        st.warning("No Dispenser columns found")
    else:
        disp_df = (
            filtered_df
            .groupby("DATE", as_index=False)[DISP_COLS]
            .sum()
        )

        if disp_df.empty:
            st.warning("No data available for selected filters")
        else:
            fig = px.line(
                disp_df,
                x="DATE",
                y=DISP_COLS,
                markers=True
            )

            fig.update_layout(
                legend_title_text="Dispenser",
                xaxis_title="Date",
                yaxis_title="Quantity"
            )

            st.plotly_chart(fig, use_container_width=True)
