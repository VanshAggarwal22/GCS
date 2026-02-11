import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import date

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="Gas Sales Dashboard", layout="wide")

GOOGLE_SHEET_ID = "1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA"
GID = "1671830441"

CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid={GID}"

# -------------------------
# DATA LOADER
# -------------------------
@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_csv(CSV_URL, header=None)

    # Drop fully empty rows
    df.dropna(how="all", inplace=True)

    # Assume header row is the first non-empty row
    header_row_idx = df.notna().all(axis=1).idxmax()
    headers = df.loc[header_row_idx].astype(str).str.strip()
    df = df.loc[header_row_idx + 1:]
    df.columns = headers

    # De-duplicate column names
    df.columns = pd.Index(pd.io.parsers.ParserBase({"names": df.columns})._maybe_dedup_names(df.columns))

    # Strip spaces
    df.columns = df.columns.str.upper().str.strip()

    return df.reset_index(drop=True)

df = load_data()

# -------------------------
# COLUMN DETECTION
# -------------------------
def find_col(patterns):
    for col in df.columns:
        for p in patterns:
            if re.search(p, col):
                return col
    return None

DATE_COL = find_col([r"DATE"])
SHIFT_COL = find_col([r"SHIFT", r"A/B/C"])
QTY_COL = find_col([r"QTY", r"KG"])
CASH_COL = find_col([r"CASH"])
RTGS_COL = find_col([r"RTGS"])
PID_COL = find_col([r"PID"])

required = {
    "DATE": DATE_COL,
    "SHIFT": SHIFT_COL,
    "QTY": QTY_COL
}

missing = [k for k, v in required.items() if v is None]
if missing:
    st.error(f"❌ Missing required columns: {missing}")
    st.stop()

# -------------------------
# CLEAN DATA
# -------------------------
df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
df = df.dropna(subset=[DATE_COL])

if df.empty:
    st.error("❌ No valid DATE values found.")
    st.stop()

# Normalize shifts
df[SHIFT_COL] = df[SHIFT_COL].astype(str).str.upper().str.strip()

# Convert numerics safely
for c in [QTY_COL, CASH_COL, RTGS_COL, PID_COL]:
    if c:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

# -------------------------
# SIDEBAR FILTERS (SAFE)
# -------------------------
min_date = df[DATE_COL].min().date()
max_date = df[DATE_COL].max().date()

date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) != 2:
    st.stop()

start_date, end_date = date_range

mask = (
    (df[DATE_COL].dt.date >= start_date) &
    (df[DATE_COL].dt.date <= end_date)
)
fdf = df.loc[mask].copy()

# -------------------------
# TABS
# -------------------------
tab1, tab2, tab3 = st.tabs([
    "📊 Daily Overview",
    "🔁 Shift-wise Analysis",
    "📅 Daily Metrics"
])

# =========================
# TAB 1 — DAILY OVERVIEW (UNCHANGED LOGIC)
# =========================
with tab1:
    st.subheader("Daily Gas Sales")

    daily = fdf.groupby(fdf[DATE_COL].dt.date).agg(
        TOTAL_QTY=(QTY_COL, "sum"),
        TOTAL_CASH=(CASH_COL, "sum") if CASH_COL else ("DATE", "count"),
        TOTAL_RTGS=(RTGS_COL, "sum") if RTGS_COL else ("DATE", "count"),
        TOTAL_PID=(PID_COL, "sum") if PID_COL else ("DATE", "count"),
    ).reset_index().rename(columns={DATE_COL: "DATE"})

    fig = px.line(
        daily,
        x="DATE",
        y="TOTAL_QTY",
        markers=True,
        title="Daily Gas Sales (KG)"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(daily, use_container_width=True)

# =========================
# TAB 2 — SHIFT-WISE ANALYSIS (FIXED)
# =========================
with tab2:
    st.subheader("Shift-wise Performance")

    shift_daily = fdf.groupby(
        [fdf[DATE_COL].dt.date, SHIFT_COL]
    ).agg(
        QTY=(QTY_COL, "sum"),
        CASH=(CASH_COL, "sum") if CASH_COL else ("DATE", "count"),
    ).reset_index().rename(columns={DATE_COL: "DATE"})

    fig2 = px.bar(
        shift_daily,
        x="DATE",
        y="QTY",
        color=SHIFT_COL,
        barmode="group",
        title="Shift-wise Gas Sales (KG)"
    )
    st.plotly_chart(fig2, use_container_width=True)

    fig3 = px.bar(
        shift_daily,
        x="DATE",
        y="CASH",
        color=SHIFT_COL,
        barmode="group",
        title="Shift-wise Cash Collection"
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.dataframe(shift_daily, use_container_width=True)

# =========================
# TAB 3 — DAILY METRICS (NEW)
# =========================
with tab3:
    st.subheader("Daily Financial Metrics")

    metrics = fdf.groupby(fdf[DATE_COL].dt.date).agg(
        TOTAL_QTY=(QTY_COL, "sum"),
        TOTAL_CASH=(CASH_COL, "sum") if CASH_COL else ("DATE", "count"),
        TOTAL_RTGS=(RTGS_COL, "sum") if RTGS_COL else ("DATE", "count"),
        TOTAL_PID=(PID_COL, "sum") if PID_COL else ("DATE", "count"),
    ).reset_index().rename(columns={DATE_COL: "DATE"})

    st.dataframe(metrics, use_container_width=True)

    fig4 = px.line(
        metrics,
        x="DATE",
        y=["TOTAL_CASH", "TOTAL_RTGS", "TOTAL_PID"],
        markers=True,
        title="Daily Payment Breakdown"
    )
    st.plotly_chart(fig4, use_container_width=True)
