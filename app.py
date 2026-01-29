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
# SAFE COLUMN DEDUPLICATION
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
# LOAD & CLEAN DATA (AUTO HEADER + ALL DATES)
# =====================================================
@st.cache_data(show_spinner=False)
def load_data():
    raw = pd.read_csv(CSV_URL, header=None)

    # Auto-detect header row
    header_row = None
    for i in range(len(raw)):
        row = raw.iloc[i].astype(str).str.upper().tolist()
        if any("DATE" in v or "DAY" in v for v in row):
            header_row = i
            break

    if header_row is None:
        st.error("❌ Could not detect header row")
        st.stop()

    raw.columns = raw.iloc[header_row]
    df = raw.iloc[header_row + 1:].copy()

    # Normalize column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(" ", "_")
        .str.replace("/", "_")
    )

    df.columns = dedup_columns(df.columns)
    df = df.dropna(how="all")

    # DATE = first column
    df["DATE"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")

    # SHIFT = second column
    df["SHIFT"] = df.iloc[:, 1].astype(str).str.strip()

    # Convert everything else numeric
    for col in df.columns[2:]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df.dropna(subset=["DATE"])
    return df

df = load_data()

# =====================================================
# SMART COLUMN MAPPING (THIS IS THE KEY FIX)
# =====================================================
COLUMN_GROUPS = {
    "CASH": ["CASH"],
    "RTGS": ["RTGS", "NEFT", "ONLINE", "BANK", "DIGITAL"],
    "PID": ["PID"],
    "TOTAL": ["TOTAL", "GRAND"]
}

def resolve_column(group_name):
    keywords = COLUMN_GROUPS[group_name]
    for col in df.columns:
        for key in keywords:
            if key in col:
                return col
    # If not found, create safe zero column
    df[group_name] = 0
    return group_name

CASH_COL = resolve_column("CASH")
RTGS_COL = resolve_column("RTGS")
PID_COL = resolve_column("PID")
TOTAL_COL = resolve_column("TOTAL")

DISP_COLS = [c for c in df.columns if "DISP" in c or "NOZZLE" in c]

# =====================================================
# SIDEBAR FILTERS
# =====================================================
st.sidebar.title("Filters")

min_date = df["DATE"].min()
max_date = df["DATE"].max()

date_range = st.sidebar.date_input(
    "Date Range",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

shift_options = sorted(df["SHIFT"].unique())

selected_shifts = st.sidebar.multiselect(
    "Shifts",
    shift_options,
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
# TAB 1 — DAILY OVERVIEW (SAFE)
# =====================================================
with tab1:
    daily = filtered_df.groupby("DATE", as_index=False).agg({
        CASH_COL: "sum",
        RTGS_COL: "sum",
        PID_COL: "sum",
        TOTAL_COL: "sum"
    })

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash", f"₹ {daily[CASH_COL].sum():,.0f}")
    c2.metric("RTGS / Online", f"₹ {daily[RTGS_COL].sum():,.0f}")
    c3.metric("PID", f"₹ {daily[PID_COL].sum():,.0f}")
    c4.metric("Total", f"₹ {daily[TOTAL_COL].sum():,.0f}")

    st.dataframe(daily, use_container_width=True)

# =====================================================
# TAB 2 — SHIFT-WISE (CORRECT)
# =====================================================
with tab2:
    shift_daily = filtered_df.groupby(["DATE", "SHIFT"], as_index=False).agg({
        CASH_COL: "sum",
        RTGS_COL: "sum",
        PID_COL: "sum",
        TOTAL_COL: "sum"
    })

    st.dataframe(shift_daily, use_container_width=True)

    shift_totals = filtered_df.groupby("SHIFT", as_index=False).agg({
        CASH_COL: "sum",
        RTGS_COL: "sum",
        PID_COL: "sum",
        TOTAL_COL: "sum"
    })

    st.dataframe(shift_totals, use_container_width=True)

# =====================================================
# TAB 3 — DAILY METRICS
# =====================================================
with tab3:
    selected_date = st.selectbox(
        "Select Date",
        sorted(filtered_df["DATE"].dt.date.unique())
    )

    day_df = filtered_df[filtered_df["DATE"].dt.date == selected_date]

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
    if DISP_COLS:
        disp_df = filtered_df.groupby("DATE", as_index=False)[DISP_COLS].sum()
        fig = px.line(disp_df, x="DATE", y=DISP_COLS, markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No dispenser columns detected")
