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
# HELPER: EXTRACT SHEET ID FROM LINK
# --------------------------------------------------
def extract_sheet_id(link):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", link)
    return match.group(1) if match else None


# ==================================================
# DAILY LOADER (New GID Based)
# ==================================================
def load_daily_sheet(link, gid):

    sheet_id = extract_sheet_id(link)

    if not sheet_id:
        st.error("Invalid Google Sheet link.")
        return None

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    try:
        raw = pd.read_csv(csv_url, header=None)
    except:
        st.error("Unable to fetch sheet. Make sure it is public.")
        return None

    # Find CONSOLIDATE DATA section
    start_row = None
    for i in range(len(raw)):
        if raw.iloc[i].astype(str).str.contains("CONSOLIDATE", case=False).any():
            start_row = i
            break

    if start_row is None:
        st.error("Consolidate data section not found.")
        return None

    header_row = start_row + 1
    data_start = header_row + 1

    headers = raw.iloc[header_row].dropna().tolist()
    df = raw.iloc[data_start:data_start + 6, :len(headers)].copy()
    df.columns = headers
    df = df.dropna(how="all")

    # Numeric cleaning
    for col in df.columns:
        if col.upper() != "SHIFT":
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce"
            ).fillna(0)

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
# 1️⃣ DAILY LINK ENTRY
# ==================================================
if page == "Daily Link Entry":

    st.title("📅 Add Daily Sheet Link")

    selected_date = st.date_input("Select Date")
    link = st.text_input("Paste Full Google Sheet Link")
    gid = st.text_input("Enter GID (Sheet ID of that date tab)")

    if st.button("Save Daily Link"):
        if link and gid:
            st.session_state.daily_links[str(selected_date)] = {
                "link": link,
                "gid": gid
            }
            st.success("Daily link saved successfully")
        else:
            st.warning("Please enter both Link and GID.")

    st.subheader("Saved Daily Links")
    st.write(st.session_state.daily_links)


# ==================================================
# 2️⃣ DAILY DASHBOARD
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

        entry = st.session_state.daily_links[selected_date]
        df = load_daily_sheet(entry["link"], entry["gid"])

        if df is not None:

            if "SHIFT" not in df.columns:
                st.error("SHIFT column not found.")
            else:
                total_row = df[df["SHIFT"].astype(str).str.upper() == "TOTAL"]

                if total_row.empty:
                    st.error("TOTAL row not found.")
                else:
                    total_row = total_row.iloc[0]

                    def safe(col):
                        return total_row[col] if col in total_row else 0

                    k1, k2, k3, k4, k5 = st.columns(5)

                    k1.metric("🔥 Gas Sold (KG)", f"{safe('QTY'):,.0f}")
                    k2.metric("💰 Sale Amount (₹)", f"{safe('SALE AMOUNT'):,.0f}")
                    k3.metric("💵 Cash (₹)", f"{safe('CASH'):,.0f}")
                    k4.metric("📲 Paytm (₹)", f"{safe('PAYTM'):,.0f}")
                    k5.metric("💳 Credit (₹)", f"{safe('CREDIT SALE'):,.0f}")

                    st.divider()

                    st.subheader("📄 Shift Breakdown")
                    st.dataframe(df, use_container_width=True)


# ==================================================
# 3️⃣ MONTHLY LINK MANAGER (ORIGINAL)
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
# 4️⃣ MONTHLY DASHBOARD (ORIGINAL EXACT LOGIC)
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

        # Make unique columns
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
