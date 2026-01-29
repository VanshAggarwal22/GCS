import streamlit as st
import pandas as pd

st.set_page_config(page_title="Daily Collection Dashboard", layout="wide")

# =====================================================
# GOOGLE SHEET CONFIG
# =====================================================
SHEET_ID = "1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA"
GID = "1671830441"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(show_spinner=False)
def load_data():
    # Load raw without headers
    raw = pd.read_csv(CSV_URL, header=None)

    # 🔴 THIS IS THE KEY LINE
    HEADER_ROW_INDEX = 3   # <-- row where actual column names exist (0-based)

    raw.columns = raw.iloc[HEADER_ROW_INDEX]
    df = raw.iloc[HEADER_ROW_INDEX + 1:].copy()

    # Clean column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(" ", "_")
    )

    # Drop completely empty rows
    df = df.dropna(how="all")

    # -----------------------------
    # DATE COLUMN (FIRST COLUMN)
    # -----------------------------
    df["DATE"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")

    # -----------------------------
    # SHIFT COLUMN (A / B / C)
    # -----------------------------
    df["SHIFT"] = df.iloc[:, 1].astype(str).str.strip()

    # -----------------------------
    # NUMERIC COLUMNS
    # -----------------------------
    for col in df.columns[2:]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

df = load_data()

# =====================================================
# COLUMN MAPPING (BASED ON YOUR SHEET)
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

# =====================================================
# TABS
# =====================================================
tab1, tab2, tab3 = st.tabs([
    "📊 Daily Overview",
    "🔁 Shift-wise Analysis",
    "📅 Daily Metrics"
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
# TAB 2 — SHIFT-WISE ANALYSIS (FIXED)
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
# TAB 3 — DAILY METRICS (ISOLATED)
# =====================================================
with tab3:
    st.subheader("Daily Metrics")

    selected_date = st.selectbox(
        "Select Date",
        sorted(filtered_df["DATE"].dropna().dt.date.unique())
    )

    day_df = filtered_df[filtered_df["DATE"].dt.date == selected_date]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash", f"₹ {day_df[CASH_COL].sum():,.0f}")
    c2.metric("RTGS", f"₹ {day_df[RTGS_COL].sum():,.0f}")
    c3.metric("PID", f"₹ {day_df[PID_COL].sum():,.0f}")
    c4.metric("Total", f"₹ {day_df[TOTAL_COL].sum():,.0f}")

    st.markdown("### Shift-wise Breakdown")
    st.dataframe(
        day_df.groupby("SHIFT", as_index=False).agg({
            CASH_COL: "sum",
            RTGS_COL: "sum",
            PID_COL: "sum",
            TOTAL_COL: "sum"
        }),
        use_container_width=True
    )
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Daily Collection Dashboard", layout="wide")

# =====================================================
# GOOGLE SHEET CONFIG
# =====================================================
SHEET_ID = "1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA"
GID = "1671830441"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(show_spinner=False)
def load_data():
    # Load raw without headers
    raw = pd.read_csv(CSV_URL, header=None)

    # 🔴 THIS IS THE KEY LINE
    HEADER_ROW_INDEX = 3   # <-- row where actual column names exist (0-based)

    raw.columns = raw.iloc[HEADER_ROW_INDEX]
    df = raw.iloc[HEADER_ROW_INDEX + 1:].copy()

    # Clean column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(" ", "_")
    )

    # Drop completely empty rows
    df = df.dropna(how="all")

    # -----------------------------
    # DATE COLUMN (FIRST COLUMN)
    # -----------------------------
    df["DATE"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")

    # -----------------------------
    # SHIFT COLUMN (A / B / C)
    # -----------------------------
    df["SHIFT"] = df.iloc[:, 1].astype(str).str.strip()

    # -----------------------------
    # NUMERIC COLUMNS
    # -----------------------------
    for col in df.columns[2:]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

df = load_data()

# =====================================================
# COLUMN MAPPING (BASED ON YOUR SHEET)
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

# =====================================================
# TABS
# =====================================================
tab1, tab2, tab3 = st.tabs([
    "📊 Daily Overview",
    "🔁 Shift-wise Analysis",
    "📅 Daily Metrics"
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
# TAB 2 — SHIFT-WISE ANALYSIS (FIXED)
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
# TAB 3 — DAILY METRICS (ISOLATED)
# =====================================================
with tab3:
    st.subheader("Daily Metrics")

    selected_date = st.selectbox(
        "Select Date",
        sorted(filtered_df["DATE"].dropna().dt.date.unique())
    )

    day_df = filtered_df[filtered_df["DATE"].dt.date == selected_date]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash", f"₹ {day_df[CASH_COL].sum():,.0f}")
    c2.metric("RTGS", f"₹ {day_df[RTGS_COL].sum():,.0f}")
    c3.metric("PID", f"₹ {day_df[PID_COL].sum():,.0f}")
    c4.metric("Total", f"₹ {day_df[TOTAL_COL].sum():,.0f}")

    st.markdown("### Shift-wise Breakdown")
    st.dataframe(
        day_df.groupby("SHIFT", as_index=False).agg({
            CASH_COL: "sum",
            RTGS_COL: "sum",
            PID_COL: "sum",
            TOTAL_COL: "sum"
        }),
        use_container_width=True
    )
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Daily Collection Dashboard", layout="wide")

# =====================================================
# GOOGLE SHEET CONFIG
# =====================================================
SHEET_ID = "1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA"
GID = "1671830441"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(show_spinner=False)
def load_data():
    # Load raw without headers
    raw = pd.read_csv(CSV_URL, header=None)

    # 🔴 THIS IS THE KEY LINE
    HEADER_ROW_INDEX = 3   # <-- row where actual column names exist (0-based)

    raw.columns = raw.iloc[HEADER_ROW_INDEX]
    df = raw.iloc[HEADER_ROW_INDEX + 1:].copy()

    # Clean column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace(" ", "_")
    )

    # Drop completely empty rows
    df = df.dropna(how="all")

    # -----------------------------
    # DATE COLUMN (FIRST COLUMN)
    # -----------------------------
    df["DATE"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")

    # -----------------------------
    # SHIFT COLUMN (A / B / C)
    # -----------------------------
    df["SHIFT"] = df.iloc[:, 1].astype(str).str.strip()

    # -----------------------------
    # NUMERIC COLUMNS
    # -----------------------------
    for col in df.columns[2:]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

df = load_data()

# =====================================================
# COLUMN MAPPING (BASED ON YOUR SHEET)
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

# =====================================================
# TABS
# =====================================================
tab1, tab2, tab3 = st.tabs([
    "📊 Daily Overview",
    "🔁 Shift-wise Analysis",
    "📅 Daily Metrics"
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
# TAB 2 — SHIFT-WISE ANALYSIS (FIXED)
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
# TAB 3 — DAILY METRICS (ISOLATED)
# =====================================================
with tab3:
    st.subheader("Daily Metrics")

    selected_date = st.selectbox(
        "Select Date",
        sorted(filtered_df["DATE"].dropna().dt.date.unique())
    )

    day_df = filtered_df[filtered_df["DATE"].dt.date == selected_date]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash", f"₹ {day_df[CASH_COL].sum():,.0f}")
    c2.metric("RTGS", f"₹ {day_df[RTGS_COL].sum():,.0f}")
    c3.metric("PID", f"₹ {day_df[PID_COL].sum():,.0f}")
    c4.metric("Total", f"₹ {day_df[TOTAL_COL].sum():,.0f}")

    st.markdown("### Shift-wise Breakdown")
    st.dataframe(
        day_df.groupby("SHIFT", as_index=False).agg({
            CASH_COL: "sum",
            RTGS_COL: "sum",
            PID_COL: "sum",
            TOTAL_COL: "sum"
        }),
        use_container_width=True
    )
