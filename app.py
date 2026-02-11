import streamlit as st
import pandas as pd
import plotly.express as px
import re
import numpy as np

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="CNG Intelligence Dashboard", layout="wide")

# --------------------------------------------------
# SESSION STATE STORAGE
# --------------------------------------------------
if "daily_links" not in st.session_state:
    st.session_state.daily_links = {}

if "monthly_links" not in st.session_state:
    st.session_state.monthly_links = {}

# --------------------------------------------------
# EXTRACT SHEET ID
# --------------------------------------------------
def extract_sheet_id(link):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", link)
    return match.group(1) if match else None

# --------------------------------------------------
# EXTRACT GID
# --------------------------------------------------
def extract_gid(link):
    match = re.search(r"gid=([0-9]+)", link)
    return match.group(1) if match else None


# ==================================================
# DAILY LOADER (AUTO SHEET ID + GID)
# ==================================================
# ==================================================
# DAILY LOADER (READ FIXED RANGE AA7:AI14)
# ==================================================
def load_daily_sheet(link):

    sheet_id = extract_sheet_id(link)
    gid = extract_gid(link)

    if not sheet_id or not gid:
        st.error("Invalid Google Sheet link. Must contain sheet id and gid.")
        return None

    # Google Sheets CSV export
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    try:
        raw = pd.read_csv(csv_url, header=None)
    except:
        st.error("Unable to fetch sheet. Make sure it is public.")
        return None

    # --------------------------------------
    # AA to AI → column index 26 to 34
    # Row 7 to 14 → index 6 to 13
    # --------------------------------------

    df = raw.iloc[6:14, 26:35].copy()

    # First row becomes header
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)

    # Clean numeric columns
    for col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .replace("nan", "0")
        )
        df[col] = pd.to_numeric(df[col], errors="ignore")

    return df



# --------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------
st.sidebar.title("📊 Navigation")

page = st.sidebar.radio(
    "Select View",
    [
        "Daily Link Entry",
        "Daily Dashboard",
        "Monthly Link Manager",
        "Monthly Dashboard"
    ]
)

# ==================================================
# 1️⃣ DAILY LINK ENTRY (ONLY LINK NOW)
# ==================================================
if page == "Daily Link Entry":

    st.title("📅 Add Daily Sheet Link")

    selected_date = st.date_input("Select Date")
    link = st.text_input("Paste Full Google Sheet Link")

    if st.button("Save Daily Link"):
        if link:
            st.session_state.daily_links[str(selected_date)] = link
            st.success("Daily link saved successfully")
        else:
            st.warning("Please enter a valid Google Sheet link.")

    st.subheader("Saved Daily Links")
    st.write(st.session_state.daily_links)


# ==================================================
# 2️⃣ DAILY DASHBOARD (FIXED - NO TOTAL DEPENDENCY)
# ==================================================
if page == "Daily Dashboard":

    st.title("📈 Daily Operations Dashboard")

    if not st.session_state.daily_links:
        st.warning("No daily links added yet.")
    else:

        selected_date = st.selectbox(
            "Select Date",
            list(st.session_state.daily_links.keys())
        )

        link = st.session_state.daily_links[selected_date]
        df = load_daily_sheet(link)

        if df is not None:

            if "SHIFT" not in df.columns:
                st.error("SHIFT column not found.")
            else:
                # Exclude TOTAL row if present
                shift_data = df[
                    ~df["SHIFT"].astype(str).str.upper().str.contains("TOTAL", na=False)
                ]

                if shift_data.empty:
                    st.error("No usable shift data found.")
                else:
                    totals = shift_data.sum(numeric_only=True)

                    def safe(col):
                        return totals[col] if col in totals else 0

                    k1, k2, k3, k4, k5 = st.columns(5)

                    k1.metric("🔥 Gas Sold (KG)", f"{safe('QTY'):,.0f}")
                    k2.metric("💰 Sale Amount (₹)", f"{safe('SALE AMOUNT'):,.0f}")
                    k3.metric("💵 Cash (₹)", f"{safe('CASH'):,.0f}")
                    k4.metric("📲 Paytm (₹)", f"{safe('PAYTM'):,.0f}")
                    k5.metric("💳 Credit (₹)", f"{safe('CREDIT SALE'):,.0f}")

                    st.divider()

                    st.subheader("📄 Shift Breakdown")
                    st.dataframe(shift_data, use_container_width=True)


# ==================================================
# 3️⃣ MONTHLY LINK MANAGER (UNCHANGED ORIGINAL)
# ==================================================
if page == "Monthly Link Manager":

    st.title("📆 Add Monthly Sheet Link")

    month_name = st.text_input("Enter Month Name (Example: March 2026)")
    link = st.text_input("Paste Full Google Sheet Link")

    if st.button("Save Monthly Link"):
        if month_name and link:
            st.session_state.monthly_links[month_name] = link
            st.success("Monthly link saved successfully")

    st.subheader("Saved Monthly Links")
    st.write(st.session_state.monthly_links)


# ==================================================
# 4️⃣ MONTHLY DASHBOARD (ORIGINAL)
# ==================================================
if page == "Monthly Dashboard":

    st.title("🚀 Monthly Operations Dashboard")

    if not st.session_state.monthly_links:
        st.warning("No monthly links added yet.")
    else:

        selected_month = st.selectbox(
            "Select Month",
            list(st.session_state.monthly_links.keys())
        )

        link = st.session_state.monthly_links[selected_month]

        sheet_id = extract_sheet_id(link)
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

        try:
            raw = pd.read_csv(csv_url, header=2)
        except:
            st.error("Unable to fetch sheet.")
            st.stop()

        raw.columns = raw.iloc[0]
        df = raw.iloc[1:].copy()

        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.upper()
            .str.replace("\n", " ")
        )

        def make_unique(cols):
            seen = {}
            new_cols = []
            for col in cols:
                if col not in seen:
                    seen[col] = 0
                    new_cols.append(col)
                else:
                    seen[col] += 1
                    new_cols.append(f"{col}_{seen[col]}")
            return new_cols

        df.columns = make_unique(df.columns)

        if "SHIFT" in df.columns:
            df["SHIFT"] = df["SHIFT"].astype(str).str.strip()
            df = df[df["SHIFT"].isin(["A", "B", "C"])]

        if "DATE" in df.columns:
            df["DATE"] = df["DATE"].ffill()
            df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce")
            df = df.dropna(subset=["DATE"])

        for col in df.columns:
            if col not in ["DATE", "SHIFT"]:
                df[col] = (
                    df[col].astype(str)
                    .str.replace(",", "", regex=False)
                    .replace("nan", "0")
                )
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        daily = df.groupby("DATE", as_index=False).sum(numeric_only=True)

        date_range = st.sidebar.date_input(
            "Select Date Range",
            [daily["DATE"].min(), daily["DATE"].max()]
        )

        daily = daily[
            (daily["DATE"] >= pd.to_datetime(date_range[0])) &
            (daily["DATE"] <= pd.to_datetime(date_range[1]))
        ]

        def safe(col):
            return daily[col].sum() if col in daily.columns else 0

        k1, k2, k3, k4, k5 = st.columns(5)

        k1.metric("🔥 Total Gas (KG)", f"{safe('TOTAL DSR QTY. KG'):,.0f}")
        k2.metric("💳 Credit (₹)", f"{safe('CREDIT SALE (RS.)'):,.0f}")
        k3.metric("💰 Paytm (₹)", f"{safe('PAYTM'):,.0f}")
        k4.metric("🏦 Cash Deposit (₹)", f"{safe('CASH DEPOSIIT IN BANK'):,.0f}")
        k5.metric("⚠️ Short Amount (₹)", f"{safe('SHORT AMOUNT'):,.0f}")

        st.divider()

        if "TOTAL DSR QTY. KG" in daily.columns:
            fig = px.line(
                daily,
                x="DATE",
                y="TOTAL DSR QTY. KG",
                markers=True,
                title="Monthly Gas Trend"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📄 Monthly Data")
        st.dataframe(daily, use_container_width=True)
