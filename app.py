import streamlit as st
import pandas as pd
import os
import glob
import numpy as np

st.set_page_config(layout="wide")
st.title("IMD Grid Climate Dashboard")

# ======================================================
# SIDEBAR
# ======================================================

st.sidebar.header("Filters")

parameter = st.sidebar.selectbox(
    "Select Parameter",
    ["rainfall", "tmax", "tmin"]
)

data_folder = os.path.join("data", parameter)
parquet_files = glob.glob(os.path.join(data_folder, "*.parquet"))

if not parquet_files:
    st.error("No parquet files found.")
    st.stop()

years = sorted([
    os.path.basename(f).split("_")[0]
    for f in parquet_files
])

selected_year = st.sidebar.selectbox("Select Year", years)

@st.cache_data
def load_year_data(parameter, year):
    possible_files = glob.glob(
        os.path.join("data", parameter, f"{year}*.parquet")
    )

    if not possible_files:
        return None

    df = pd.read_parquet(possible_files[0])
    df.columns = df.columns.str.lower()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


df = load_year_data(parameter, selected_year)

if df is None:
    st.error("Could not load selected year file.")
    st.stop()

min_date = df["date"].min()
max_date = df["date"].max()

selected_date = st.sidebar.date_input(
    "Select Date",
    value=min_date,
    min_value=min_date,
    max_value=max_date
)

lat_input = st.sidebar.text_input("Enter Latitude (e.g. 19.5)")
lon_input = st.sidebar.text_input("Enter Longitude (e.g. 80.25)")

# ======================================================
# GRID RESOLUTION LOGIC
# ======================================================

grid_size_map = {
    "rainfall": 0.25,
    "tmax": 1.0,
    "tmin": 1.0
}

grid_size = grid_size_map[parameter]

# ======================================================
# MAIN LOGIC
# ======================================================

if lat_input and lon_input:

    try:
        lat_val = float(lat_input)
        lon_val = float(lon_input)

        selected_date = pd.to_datetime(selected_date)

        # Snap to nearest grid based on resolution
        snapped_lat = round(lat_val / grid_size) * grid_size
        snapped_lon = round(lon_val / grid_size) * grid_size

        # Filter by date
        date_filtered = df[df["date"] == selected_date]

        if date_filtered.empty:
            st.warning("No data available for selected date.")
            st.stop()

        value_column = {
            "rainfall": "rain",
            "tmax": "tmax",
            "tmin": "tmin"
        }.get(parameter, "rain")

        # Ensure numeric
        date_filtered["lat"] = pd.to_numeric(date_filtered["lat"], errors="coerce")
        date_filtered["lon"] = pd.to_numeric(date_filtered["lon"], errors="coerce")
        date_filtered[value_column] = pd.to_numeric(
            date_filtered[value_column], errors="coerce"
        )

        clean_df = date_filtered.dropna(
            subset=["lat", "lon", value_column]
        )

        if clean_df.empty:
            st.error("All values for this date are NaN.")
            st.stop()

        # Exact match after snapping
        final_row = clean_df[
            (clean_df["lat"] == snapped_lat) &
            (clean_df["lon"] == snapped_lon)
        ]

        if final_row.empty:
            st.warning("Snapped grid point not found in dataset.")
            st.stop()

        value = final_row.iloc[0][value_column]

        # ==================================================
        # DISPLAY
        # ==================================================

        st.success("Grid Value Found")

        col1, col2 = st.columns(2)

        with col1:
            st.write("Requested Latitude:", lat_val)
            st.write("Requested Longitude:", lon_val)
            st.write("Snapped Latitude:", snapped_lat)
            st.write("Snapped Longitude:", snapped_lon)

        with col2:
            st.write("Date:", selected_date.date())
            st.write("Parameter:", parameter)
            st.write("Grid Resolution:", f"{grid_size}°")
            st.write("Value:", value)

    except ValueError:
        st.error("Latitude and Longitude must be numeric.")

else:
    st.info("Enter latitude and longitude to fetch data.")
