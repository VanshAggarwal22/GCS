import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import re

st.set_page_config(layout="wide")
st.title("📊 Business Dashboard")

# =========================================================
# Helper Function – Clean Numeric Columns Safely
# =========================================================

def clean_numeric_column(series):
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0)

# =========================================================
# TABS
# =========================================================

tab1, tab2 = st.tabs(["📆 Monthly Dashboard", "📅 Daily Dashboard"])

# =========================================================
# 📆 MONTHLY TAB (Original Style – Stable)
# =========================================================

with tab1:

    st.header("Monthly Dashboard")

    uploaded_file = st.file_uploader(
        "Upload Monthly Excel File",
        type=["xlsx"]
    )

    if uploaded_file:

        try:
            df = pd.read_excel(uploaded_file)

            df.columns = df.columns.str.strip()
            df = df.dropna(how="all")

            # Detect numeric columns (original simple style)
            numeric_cols = []

            for col in df.columns:
                try:
                    df[col] = clean_numeric_column(df[col])
                    if df[col].sum() != 0:
                        numeric_cols.append(col)
                except:
                    pass

            st.subheader("📋 Raw Data")
            st.dataframe(df, use_container_width=True)

            if numeric_cols:

                totals = df[numeric_cols].sum()

                st.subheader("📊 Summary Stats")
                cols = st.columns(len(numeric_cols))

                for i, col in enumerate(numeric_cols):
                    cols[i].metric(
                        label=col,
                        value=f"{totals[col]:,.2f}"
                    )

                # Trend Charts
                st.subheader("📈 Trends")

                x_axis = df.columns[0]

                for col in numeric_cols:
                    fig, ax = plt.subplots()
                    ax.plot(df[x_axis], df[col])
                    ax.set_title(col)
                    ax.set_xlabel(x_axis)
                    ax.set_ylabel(col)
                    st.pyplot(fig)

        except Exception as e:
            st.error(f"Error processing file: {e}")

# =========================================================
# 📅 DAILY TAB (Dynamic + Link Based)
# =========================================================

with tab2:

    st.header("Daily Dashboard")

    daily_link = st.text_input("Paste Google Sheet link")

    if daily_link:

        try:
            # --------------------------
            # Extract Sheet ID
            # --------------------------
            sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", daily_link)
            if not sheet_id_match:
                st.error("Invalid Google Sheet link.")
                st.stop()

            sheet_id = sheet_id_match.group(1)

            # --------------------------
            # Extract GID
            # --------------------------
            gid_match = re.search(r"gid=([0-9]+)", daily_link)
            if not gid_match:
                st.error("No GID found in link.")
                st.stop()

            gid = gid_match.group(1)

            # --------------------------
            # Convert to CSV URL
            # --------------------------
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

            df = pd.read_csv(csv_url)

            if df.empty:
                st.error("No data found in sheet.")
                st.stop()

            df.columns = df.columns.str.strip()
            df = df.dropna(how="all")

            # --------------------------
            # Dynamic Numeric Detection
            # --------------------------
            numeric_cols = []

            for col in df.columns:
                cleaned_series = (
                    df[col]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.replace("₹", "", regex=False)
                    .str.strip()
                )

                converted = pd.to_numeric(cleaned_series, errors="coerce")

                if converted.notna().sum() > len(df) * 0.4:
                    df[col] = converted.fillna(0)
                    numeric_cols.append(col)

            # --------------------------
            # Display Raw Data
            # --------------------------
            st.subheader("📋 Raw Data")
            st.dataframe(df, use_container_width=True)

            # --------------------------
            # Summary Stats (Dynamic)
            # --------------------------
            if numeric_cols:

                totals = df[numeric_cols].sum()

                st.subheader("📊 Summary Stats")

                cols = st.columns(len(numeric_cols))

                for i, col in enumerate(numeric_cols):
                    cols[i].metric(
                        label=col,
                        value=f"{totals[col]:,.2f}"
                    )

            # --------------------------
            # Trends
            # --------------------------
            if numeric_cols:

                st.subheader("📈 Trends")

                x_axis = df.columns[0]

                for col in numeric_cols:
                    fig, ax = plt.subplots()
                    ax.plot(df[x_axis], df[col])
                    ax.set_title(col)
                    ax.set_xlabel(x_axis)
                    ax.set_ylabel(col)
                    st.pyplot(fig)

            # --------------------------
            # Top Performers
            # --------------------------
            if numeric_cols:

                st.subheader("🏆 Top Contributors")

                selected_metric = st.selectbox(
                    "Select Metric",
                    numeric_cols
                )

                sorted_df = df.sort_values(
                    by=selected_metric,
                    ascending=False
                )

                st.dataframe(sorted_df.head(10), use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")
