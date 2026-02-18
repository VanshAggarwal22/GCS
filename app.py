import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import re
import json
import os

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="CNG Intelligence Dashboard",
    page_icon="🔥",
    layout="wide"
)

# ==========================================================
# GOOGLE CONNECTION
# ==========================================================
@st.cache_resource
def connect_google():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )

    return gspread.authorize(credentials)


# ==========================================================
# UTILITIES
# ==========================================================
def extract_sheet_id(link):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", link)
    return match.group(1) if match else None


@st.cache_data(ttl=300)
def fetch_sheet(link, worksheet_name=None):
    client = connect_google()
    sheet_id = extract_sheet_id(link)

    spreadsheet = client.open_by_key(sheet_id)

    if worksheet_name:
        worksheet = spreadsheet.worksheet(worksheet_name)
    else:
        worksheet = spreadsheet.sheet1

    data = worksheet.get_all_values()
    df = pd.DataFrame(data)

    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)

    return df


def clean_numeric(df):
    for col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="ignore")
    return df


# ==========================================================
# LINK STORAGE
# ==========================================================
DATA_FILE = "links.json"

def load_links():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"daily": {}, "monthly": {}}

def save_links(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data_store = load_links()


# ==========================================================
# SIDEBAR
# ==========================================================
st.sidebar.title("📊 Navigation")

page = st.sidebar.radio(
    "Select Dashboard",
    ["Daily Dashboard", "Add Daily Link", "Monthly Dashboard", "Add Monthly Link"]
)


# ==========================================================
# DAILY LINK ENTRY
# ==========================================================
if page == "Add Daily Link":

    st.title("📅 Add Daily Sheet Link")

    date = st.date_input("Select Date")
    link = st.text_input("Paste Google Sheet Link")

    if st.button("Save"):
        data_store["daily"][str(date)] = link
        save_links(data_store)
        st.success("Saved Successfully")


# ==========================================================
# DAILY DASHBOARD
# ==========================================================
if page == "Daily Dashboard":

    st.title("🔥 Daily CNG Operations")

    if not data_store["daily"]:
        st.warning("No daily links added.")
        st.stop()

    dates = sorted(data_store["daily"].keys())
    selected = st.selectbox("Select Date", dates)

    link = data_store["daily"][selected]

    try:
        df = fetch_sheet(link)
        df = clean_numeric(df)
    except Exception as e:
        st.error(f"Error loading sheet: {e}")
        st.stop()

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

    if numeric_cols:

        totals = df[numeric_cols].sum()

        cols = st.columns(4)

        for i, col in enumerate(numeric_cols[:4]):
            cols[i].metric(col, f"{totals[col]:,.0f}")

        st.divider()

        fig = px.bar(
            df,
            x=df.columns[0],
            y=numeric_cols,
            barmode="group"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)


# ==========================================================
# MONTHLY LINK ENTRY
# ==========================================================
if page == "Add Monthly Link":

    st.title("📆 Add Monthly Sheet")

    month = st.text_input("Month Name")
    link = st.text_input("Paste Sheet Link")

    if st.button("Save Monthly"):
        data_store["monthly"][month] = link
        save_links(data_store)
        st.success("Saved Successfully")


# ==========================================================
# MONTHLY DASHBOARD
# ==========================================================
if page == "Monthly Dashboard":

    st.title("🚀 Monthly Intelligence")

    if not data_store["monthly"]:
        st.warning("No monthly links added.")
        st.stop()

    selected = st.selectbox(
        "Select Month",
        list(data_store["monthly"].keys())
    )

    link = data_store["monthly"][selected]

    try:
        df = fetch_sheet(link)
        df = clean_numeric(df)
    except Exception as e:
        st.error(f"Error loading sheet: {e}")
        st.stop()

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

    if "DATE" in df.columns:
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
        df = df.dropna(subset=["DATE"])

        daily = df.groupby("DATE", as_index=False).sum(numeric_only=True)

        st.metric("Total Volume", f"{daily[numeric_cols].sum().sum():,.0f}")

        fig = px.line(
            daily,
            x="DATE",
            y=numeric_cols[0],
            markers=True,
            title="Monthly Trend"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(daily, use_container_width=True)
