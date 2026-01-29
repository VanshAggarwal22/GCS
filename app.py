import streamlit as st
import pandas as pd
import plotly.express as px

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(page_title="CNG Operations Dashboard", layout="wide")
st.title("📊 CNG Station Operations Dashboard")

# ==================================================
# ========== PART 1: ROW-BASED GOOGLE SHEET =========
# ==================================================

SHEET_ID = "1pFPzyxib9rG5dune9FgUYO91Bp1zL2StO6ftxDBPRJM"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
raw = pd.read_csv(CSV_URL, header=2)

raw.columns = raw.iloc[0]
df = raw.iloc[1:].copy()

# ---------- Clean column names ----------
df.columns = (
    df.columns.astype(str)
    .str.strip()
    .str.upper()
    .str.replace("\n", " ")
)

def make_unique(cols):
    seen, out = {}, []
    for c in cols:
        if c not in seen:
            seen[c] = 0
            out.append(c)
        else:
            seen[c] += 1
            out.append(f"{c}_{seen[c]}")
    return out

df.columns = make_unique(df.columns)

# ---------- Identify DATE & SHIFT ----------
df.rename(columns={df.columns[0]: "DATE", df.columns[1]: "SHIFT"}, inplace=True)

df["SHIFT"] = df["SHIFT"].astype(str).str.strip().str.upper()
df = df[df["SHIFT"].isin(["A", "B", "C"])]

df["DATE"] = df["DATE"].ffill()
df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
df = df.dropna(subset=["DATE"])

# ---------- Numeric cleanup ----------
for c in df.columns:
    if c not in ["DATE", "SHIFT"]:
        df[c] = (
            df[c].astype(str)
            .str.replace(",", "", regex=False)
            .replace("nan", "0")
        )
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

# ==================================================
# SIDEBAR FILTER
# ==================================================
st.sidebar.header("🔎 Filters")

date_range = st.sidebar.date_input(
    "Select Date Range",
    [df["DATE"].min(), df["DATE"].max()]
)

df_f = df[
    (df["DATE"] >= pd.to_datetime(date_range[0])) &
    (df["DATE"] <= pd.to_datetime(date_range[1]))
]

# ---------- Daily aggregation (DO NOT CHANGE) ----------
daily = df_f.groupby("DATE", as_index=False).sum(numeric_only=True)

def safe(col):
    return daily[col].sum() if col in daily.columns else 0

# ==================================================
# KPI CARDS
# ==================================================
k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("🔥 Gas Sold (KG)", f"{safe('TOTAL DSR QTY. KG'):,.0f}")
k2.metric("💳 Credit (₹)", f"{safe('CREDIT SALE (RS.)'):,.0f}")
k3.metric("💰 Paytm (₹)", f"{safe('PAYTM'):,.0f}")
k4.metric("🏦 Cash Deposit (₹)", f"{safe('CASH DEPOSIIT IN BANK'):,.0f}")
k5.metric("💸 Expenses (₹)", f"{safe('EXPENSES'):,.0f}")
k6.metric("⚠️ Short Amount (₹)", f"{safe('SHORT AMOUNT'):,.0f}")

st.divider()

# ==================================================
# TABS
# ==================================================
tabs = st.tabs([
    "📈 Daily Overview",
    "🔄 Shift Analysis",
    "📊 Sheet-wise Analytics",
    "📅 Monthly Summary",
    "📄 Raw Data"
])

# ==================================================
# TAB 1: DAILY OVERVIEW (UNCHANGED)
# ==================================================
with tabs[0]:
    fig = px.line(
        daily,
        x="DATE",
        y="TOTAL DSR QTY. KG",
        markers=True,
        title="Daily Gas Sales (KG)"
    )
    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# TAB 2: SHIFT ANALYSIS (ROW-BASED)
# ==================================================
with tabs[1]:
    shift_daily = (
        df_f.groupby(["DATE", "SHIFT"], as_index=False)
        .sum(numeric_only=True)
    )

    fig_shift = px.bar(
        shift_daily,
        x="DATE",
        y="TOTAL DSR QTY. KG",
        color="SHIFT",
        barmode="group",
        title="Gas Sales by Shift (A / B / C)"
    )
    st.plotly_chart(fig_shift, use_container_width=True)

    cash_cols = [c for c in shift_daily.columns if any(
        k in c for k in ["CASH", "PAYTM", "ATM", "RTGS", "PID"]
    )]

    if cash_cols:
        cash_shift = df_f.groupby("SHIFT", as_index=False)[cash_cols].sum()

        fig_cash = px.bar(
            cash_shift.melt(id_vars="SHIFT", var_name="Mode", value_name="Amount"),
            x="SHIFT",
            y="Amount",
            color="Mode",
            barmode="stack",
            title="Shift-wise Cash / Digital Collection"
        )
        st.plotly_chart(fig_cash, use_container_width=True)

# ==================================================
# ========== PART 2: SHEET-WISE ANALYTICS ===========
# ==================================================

def extract_sheet_summary(sheet_df, sheet_name):
    data = {"DATE": sheet_name}
    sheet_df = sheet_df.fillna("")

    for i, row in sheet_df.iterrows():
        text = " ".join(row.astype(str).values)

        if "SHIFT-A" in text:
            data["SHIFT_A_QTY"] = pd.to_numeric(row[row != ""].values[-1], errors="coerce")
        if "SHIFT-B" in text:
            data["SHIFT_B_QTY"] = pd.to_numeric(row[row != ""].values[-1], errors="coerce")
        if "SHIFT-C" in text:
            data["SHIFT_C_QTY"] = pd.to_numeric(row[row != ""].values[-1], errors="coerce")
        if "TOTAL COLLECTION" in text:
            data["TOTAL_COLLECTION"] = pd.to_numeric(row[row != ""].values[-1], errors="coerce")

    payment_keys = ["CASH", "PAYTM", "ATM", "RTGS", "PID", "CREDIT"]
    for k in payment_keys:
        matches = sheet_df.apply(lambda r: k in " ".join(r.astype(str)), axis=1)
        if matches.any():
            idx = matches.idxmax()
            data[k] = pd.to_numeric(sheet_df.iloc[idx].values[-1], errors="coerce")

    return data

# ==================================================
# TAB 3: SHEET-WISE ANALYTICS
# ==================================================
with tabs[2]:
    st.subheader("📊 Sheet-wise Daily Analytics")

    excel_path = "https://docs.google.com/spreadsheets/d/1_NDdrYnUJnFoJHwc5pZUy5bM920UqMmxP2dUJErGtNA/edit?gid=1671830441#gid=1671830441"
    xls = pd.ExcelFile(excel_path)

    rows = []
    for sheet in xls.sheet_names:
        try:
            s_df = pd.read_excel(excel_path, sheet_name=sheet)
            rows.append(extract_sheet_summary(s_df, sheet))
        except:
            continue

    summary = pd.DataFrame(rows)
    summary["DATE"] = pd.to_datetime(summary["DATE"], dayfirst=True, errors="coerce")
    summary = summary.dropna(subset=["DATE"])

    st.dataframe(summary, use_container_width=True)

    fig_total = px.line(
        summary,
        x="DATE",
        y="TOTAL_COLLECTION",
        markers=True,
        title="Daily Total Collection (Sheet-wise)"
    )
    st.plotly_chart(fig_total, use_container_width=True)

# ==================================================
# TAB 4: MONTHLY SUMMARY
# ==================================================
with tabs[3]:
    daily["MONTH"] = daily["DATE"].dt.to_period("M").astype(str)
    monthly = daily.groupby("MONTH", as_index=False).sum(numeric_only=True)
    st.dataframe(monthly, use_container_width=True)

# ==================================================
# TAB 5: RAW DATA
# ==================================================
with tabs[4]:
    st.dataframe(df_f, use_container_width=True)
