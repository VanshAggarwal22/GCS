import streamlit as st
import pandas as pd
import numpy as np
import re
import plotly.express as px
from datetime import timedelta

st.set_page_config(page_title="Advanced Production Dashboard", layout="wide")

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def extract_sheet_id(link):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", link)
    return match.group(1) if match else None


def load_google_sheet(link):
    sheet_id = extract_sheet_id(link)

    if not sheet_id:
        st.error("Invalid Google Sheet link.")
        return None

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    try:
        raw = pd.read_csv(csv_url)
    except Exception as e:
        st.error("Could not fetch sheet. Make sure it is public.")
        return None

    # Clean columns
    raw.columns = (
        raw.columns.astype(str)
        .str.strip()
        .str.upper()
        .str.replace("\n", " ")
    )

    # Remove completely empty rows
    raw = raw.dropna(how="all")

    # Auto detect DATE column
    date_col = None
    for col in raw.columns:
        if "DATE" in col:
            date_col = col
            break

    if not date_col:
        st.error("No DATE column found.")
        st.write("Detected Columns:", raw.columns.tolist())
        return None

    raw.rename(columns={date_col: "DATE"}, inplace=True)

    # Convert DATE
    raw["DATE"] = pd.to_datetime(raw["DATE"], errors="coerce", dayfirst=True)
    raw = raw.dropna(subset=["DATE"])

    # Convert numeric columns safely
    for col in raw.columns:
        if col != "DATE":
            raw[col] = (
                raw[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .replace("nan", "0")
            )
            raw[col] = pd.to_numeric(raw[col], errors="coerce").fillna(0)

    return raw


def safe_groupby(df):
    if df is None:
        return None

    if "DATE" not in df.columns:
        st.error("DATE column missing.")
        return None

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

    if not numeric_cols:
        st.warning("No numeric columns found.")
        return None

    grouped = df.groupby("DATE", as_index=False)[numeric_cols].sum()
    return grouped


def forecast_next_7_days(df):
    if df is None:
        return None

    df = df.sort_values("DATE")
    last_7 = df.tail(7)

    if len(last_7) < 3:
        return None

    forecast_df = last_7.copy()
    forecast_df["DATE"] = forecast_df["DATE"].max() + timedelta(days=1)

    forecast_rows = []
    for i in range(7):
        new_row = {}
        new_row["DATE"] = df["DATE"].max() + timedelta(days=i + 1)
        for col in df.select_dtypes(include=np.number).columns:
            new_row[col] = last_7[col].mean()
        forecast_rows.append(new_row)

    return pd.DataFrame(forecast_rows)


def detect_alerts(df):
    alerts = []
    numeric_cols = df.select_dtypes(include=np.number).columns

    for col in numeric_cols:
        mean = df[col].mean()
        std = df[col].std()

        latest = df[col].iloc[-1]

        if latest > mean + 2 * std:
            alerts.append(f"⚠️ Excess spike in {col}")
        elif latest < mean - 2 * std:
            alerts.append(f"⚠️ Abnormal drop in {col}")

    return alerts


# =====================================================
# SIDEBAR NAVIGATION
# =====================================================

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Page",
    [
        "Add Daily Data",
        "Daily Dashboard",
        "Add Monthly Data",
        "Monthly Dashboard"
    ]
)

# =====================================================
# SESSION STATE
# =====================================================

if "daily_link" not in st.session_state:
    st.session_state.daily_link = None

if "monthly_links" not in st.session_state:
    st.session_state.monthly_links = []


# =====================================================
# PAGE 1: ADD DAILY DATA
# =====================================================

if page == "Add Daily Data":

    st.title("📅 Add Daily Sheet")

    link = st.text_input("Paste Daily Google Sheet Link")

    if st.button("Save Daily Link"):
        st.session_state.daily_link = link
        st.success("Daily Sheet Link Saved!")


# =====================================================
# PAGE 2: DAILY DASHBOARD
# =====================================================

elif page == "Daily Dashboard":

    st.title("📊 Daily Production Dashboard")

    if not st.session_state.daily_link:
        st.warning("Please add daily sheet link first.")
        st.stop()

    df = load_google_sheet(st.session_state.daily_link)
    daily = safe_groupby(df)

    if daily is None:
        st.stop()

    # KPIs
    col1, col2, col3 = st.columns(3)

    total_sum = daily.select_dtypes(include=np.number).sum().sum()
    avg_day = daily.select_dtypes(include=np.number).sum(axis=1).mean()
    days = len(daily)

    col1.metric("Total Production", f"{total_sum:,.0f}")
    col2.metric("Average Per Day", f"{avg_day:,.0f}")
    col3.metric("Total Days", days)

    # Trend
    for col in daily.select_dtypes(include=np.number).columns:
        fig = px.line(daily, x="DATE", y=col, title=f"{col} Trend")
        st.plotly_chart(fig, use_container_width=True)

    # Forecast
    st.subheader("🔮 7 Day Forecast")
    forecast = forecast_next_7_days(daily)

    if forecast is not None:
        st.dataframe(forecast)

    # Alerts
    st.subheader("🚨 Alerts")
    alerts = detect_alerts(daily)

    if alerts:
        for a in alerts:
            st.error(a)
    else:
        st.success("No abnormal activity detected.")


# =====================================================
# PAGE 3: ADD MONTHLY DATA
# =====================================================

elif page == "Add Monthly Data":

    st.title("📆 Add Monthly Sheet")

    link = st.text_input("Paste Monthly Google Sheet Link")

    if st.button("Add Month"):
        st.session_state.monthly_links.append(link)
        st.success("Monthly Link Added!")

    st.write("Added Months:")
    st.write(st.session_state.monthly_links)


# =====================================================
# PAGE 4: MONTHLY DASHBOARD
# =====================================================

elif page == "Monthly Dashboard":

    st.title("📈 Monthly Analytics Dashboard")

    if not st.session_state.monthly_links:
        st.warning("Please add at least one monthly link.")
        st.stop()

    all_data = []

    for link in st.session_state.monthly_links:
        df = load_google_sheet(link)
        grouped = safe_groupby(df)

        if grouped is not None:
            all_data.append(grouped)

    if not all_data:
        st.error("No valid monthly data.")
        st.stop()

    combined = pd.concat(all_data)
    combined = combined.groupby("DATE", as_index=False).sum()

    # KPIs
    col1, col2, col3 = st.columns(3)

    total_sum = combined.select_dtypes(include=np.number).sum().sum()
    avg_day = combined.select_dtypes(include=np.number).sum(axis=1).mean()
    months = len(st.session_state.monthly_links)

    col1.metric("Total Production", f"{total_sum:,.0f}")
    col2.metric("Average Per Day", f"{avg_day:,.0f}")
    col3.metric("Total Months Loaded", months)

    # Trend charts
    for col in combined.select_dtypes(include=np.number).columns:
        fig = px.line(combined, x="DATE", y=col, title=f"{col} Monthly Trend")
        st.plotly_chart(fig, use_container_width=True)

    # Forecast
    st.subheader("🔮 7 Day Forecast")
    forecast = forecast_next_7_days(combined)

    if forecast is not None:
        st.dataframe(forecast)

    # Alerts
    st.subheader("🚨 Alerts")
    alerts = detect_alerts(combined)

    if alerts:
        for a in alerts:
            st.error(a)
    else:
        st.success("No abnormal monthly activity detected.")
