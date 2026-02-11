import streamlit as st
import pandas as pd
import numpy as np
import re
import plotly.express as px
from datetime import timedelta

st.set_page_config(page_title="Production Intelligence Dashboard", layout="wide")

# =====================================================
# SAFE SHEET ID EXTRACTION (ULTRA ROBUST)
# =====================================================

def extract_sheet_id(link):
    if not link:
        return None

    try:
        if "docs.google.com" not in link:
            return None

        # Split by /d/ and take the ID
        parts = link.split("/d/")
        if len(parts) < 2:
            return None

        sheet_id = parts[1].split("/")[0]
        return sheet_id.strip()

    except:
        return None


# =====================================================
# LOAD GOOGLE SHEET
# =====================================================

def load_google_sheet(link):

    sheet_id = extract_sheet_id(link)

    if not sheet_id:
        st.error("Invalid Google Sheet link format.")
        return None

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    try:
        df = pd.read_csv(csv_url)
    except Exception as e:
        st.error("Unable to fetch sheet.")
        st.write("Possible reasons:")
        st.write("- Sheet is not public")
        st.write("- Invalid link")
        st.write("- Internet restriction")
        return None

    if df.empty:
        st.error("Sheet loaded but empty.")
        return None

    # Clean column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace("\n", " ")
    )

    # Remove empty rows
    df = df.dropna(how="all")

    # Detect DATE column automatically
    date_col = None
    for col in df.columns:
        if "DATE" in col:
            date_col = col
            break

    if not date_col:
        st.error("No DATE column detected.")
        st.write("Detected columns:", df.columns.tolist())
        return None

    df.rename(columns={date_col: "DATE"}, inplace=True)

    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["DATE"])

    # Convert numeric columns
    for col in df.columns:
        if col != "DATE":
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .replace("nan", "0")
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


# =====================================================
# SAFE GROUPBY
# =====================================================

def safe_groupby(df):
    if df is None:
        return None

    if "DATE" not in df.columns:
        return None

    numeric_cols = df.select_dtypes(include=np.number).columns

    if len(numeric_cols) == 0:
        st.error("No numeric columns found.")
        return None

    grouped = df.groupby("DATE", as_index=False)[numeric_cols].sum()
    return grouped


# =====================================================
# FORECAST (Moving Average Based)
# =====================================================

def forecast_next_7_days(df):

    if df is None or len(df) < 3:
        return None

    df = df.sort_values("DATE")
    last_date = df["DATE"].max()
    last_7 = df.tail(7)

    forecast_rows = []

    for i in range(1, 8):
        new_row = {"DATE": last_date + timedelta(days=i)}

        for col in df.select_dtypes(include=np.number).columns:
            new_row[col] = last_7[col].mean()

        forecast_rows.append(new_row)

    return pd.DataFrame(forecast_rows)


# =====================================================
# ALERT SYSTEM
# =====================================================

def detect_alerts(df):

    alerts = []

    for col in df.select_dtypes(include=np.number).columns:
        mean = df[col].mean()
        std = df[col].std()

        latest = df[col].iloc[-1]

        if latest > mean + 2 * std:
            alerts.append(f"⚠️ Spike detected in {col}")
        elif latest < mean - 2 * std:
            alerts.append(f"⚠️ Drop detected in {col}")

    return alerts


# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Page",
    [
        "Add Daily Sheet",
        "Daily Dashboard",
        "Add Monthly Sheet",
        "Monthly Dashboard"
    ]
)

if "daily_link" not in st.session_state:
    st.session_state.daily_link = None

if "monthly_links" not in st.session_state:
    st.session_state.monthly_links = []


# =====================================================
# ADD DAILY
# =====================================================

if page == "Add Daily Sheet":

    st.title("Add Daily Google Sheet")

    link = st.text_input("Paste Full Daily Sheet Link")

    if st.button("Save Daily Link"):
        st.session_state.daily_link = link
        st.success("Daily link saved.")


# =====================================================
# DAILY DASHBOARD
# =====================================================

elif page == "Daily Dashboard":

    st.title("Daily Analytics Dashboard")

    if not st.session_state.daily_link:
        st.warning("Add daily sheet first.")
        st.stop()

    df = load_google_sheet(st.session_state.daily_link)
    daily = safe_groupby(df)

    if daily is None:
        st.stop()

    total = daily.select_dtypes(include=np.number).sum().sum()
    avg = daily.select_dtypes(include=np.number).sum(axis=1).mean()

    c1, c2 = st.columns(2)
    c1.metric("Total Production", f"{total:,.0f}")
    c2.metric("Average Per Day", f"{avg:,.0f}")

    for col in daily.select_dtypes(include=np.number).columns:
        fig = px.line(daily, x="DATE", y=col, title=f"{col} Trend")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("7 Day Forecast")
    forecast = forecast_next_7_days(daily)
    if forecast is not None:
        st.dataframe(forecast)

    st.subheader("Alerts")
    alerts = detect_alerts(daily)

    if alerts:
        for a in alerts:
            st.error(a)
    else:
        st.success("No abnormal activity.")


# =====================================================
# ADD MONTHLY
# =====================================================

elif page == "Add Monthly Sheet":

    st.title("Add Monthly Google Sheet")

    link = st.text_input("Paste Full Monthly Sheet Link")

    if st.button("Add Month"):
        st.session_state.monthly_links.append(link)
        st.success("Monthly link added.")

    st.write("Current Monthly Links:")
    st.write(st.session_state.monthly_links)


# =====================================================
# MONTHLY DASHBOARD
# =====================================================

elif page == "Monthly Dashboard":

    st.title("Monthly Analytics Dashboard")

    if not st.session_state.monthly_links:
        st.warning("Add monthly sheets first.")
        st.stop()

    all_data = []

    for link in st.session_state.monthly_links:
        df = load_google_sheet(link)
        grouped = safe_groupby(df)

        if grouped is not None:
            all_data.append(grouped)

    if not all_data:
        st.error("No valid monthly data loaded.")
        st.stop()

    combined = pd.concat(all_data)
    combined = combined.groupby("DATE", as_index=False).sum()

    total = combined.select_dtypes(include=np.number).sum().sum()
    avg = combined.select_dtypes(include=np.number).sum(axis=1).mean()

    c1, c2 = st.columns(2)
    c1.metric("Total Production", f"{total:,.0f}")
    c2.metric("Average Per Day", f"{avg:,.0f}")

    for col in combined.select_dtypes(include=np.number).columns:
        fig = px.line(combined, x="DATE", y=col, title=f"{col} Monthly Trend")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("7 Day Forecast")
    forecast = forecast_next_7_days(combined)
    if forecast is not None:
        st.dataframe(forecast)

    st.subheader("Alerts")
    alerts = detect_alerts(combined)

    if alerts:
        for a in alerts:
            st.error(a)
    else:
        st.success("No abnormal monthly activity.")
