import streamlit as st
import pandas as pd
import os
import glob
import numpy as np

st.set_page_config(layout="wide")
st.title("IMD Grid Climate Dashboard")

# ======================================================
# GRID DEFINITIONS
# ======================================================

GRID_CONFIG = {
    "rainfall": {
        "resolution": 0.25,
        "lat_min": 6.5,
        "lat_max": 38.5,
        "lon_min": 66.5,
        "lon_max": 100.0
    },
    "tmax": {
        "resolution": 1.0,
        "lat_min": 7.5,
        "lat_max": 37.5,
        "lon_min": 67.5,
        "lon_max": 97.5
    },
    "tmin": {
        "resolution": 1.0,
        "lat_min": 7.5,
        "lat_max": 37.5,
        "lon_min": 67.5,
        "lon_max": 97.5
    }
}

# ======================================================
# SIDEBAR
# ======================================================

st.sidebar.header("Filters")

parameter = st.sidebar.selectbox(
    "Select Parameter",
    ["rainfall", "tmax", "tmin"]
)

config = GRID_CONFIG[parameter]

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

# ======================================================
# LOAD DATA
# ======================================================

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

    # Convert to numeric
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    # Auto-fix swapped columns
    if df["lon"].max() <= 40:
        df.rename(columns={"lon": "temp_lat"}, inplace=True)
        df.rename(columns={"lat": "lon"}, inplace=True)
        df.rename(columns={"temp_lat": "lat"}, inplace=True)
        st.warning("Lat/Lon columns were swapped automatically.")

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

lat_input = st.sidebar.text_input("Enter Latitude")
lon_input = st.sidebar.text_input("Enter Longitude")

# ======================================================
# MAIN LOGIC
# ======================================================

if lat_input and lon_input:

    try:
        lat_val = float(lat_input)
        lon_val = float(lon_input)

        # -------------------------------
        # 1️⃣ CHECK BOUNDS
        # -------------------------------

        if not (config["lat_min"] <= lat_val <= config["lat_max"]):
            st.error("Latitude outside IMD grid bounds.")
            st.stop()

        if not (config["lon_min"] <= lon_val <= config["lon_max"]):
            st.error("Longitude outside IMD grid bounds.")
            st.stop()

        selected_date = pd.to_datetime(selected_date)

        date_filtered = df[df["date"] == selected_date]

        if date_filtered.empty:
            st.warning("No data available for selected date.")
            st.stop()

        value_column = {
            "rainfall": "rain",
            "tmax": "tmax",
            "tmin": "tmin"
        }.get(parameter, "rain")

        date_filtered[value_column] = pd.to_numeric(
            date_filtered[value_column], errors="coerce"
        )

        clean_df = date_filtered.dropna(
            subset=["lat", "lon", value_column]
        )

        if clean_df.empty:
            st.error("All values for this date are NaN.")
            st.stop()

        # -------------------------------
        # 2️⃣ SNAP TO GRID RESOLUTION
        # -------------------------------

        res = config["resolution"]

        snapped_lat = round((lat_val - config["lat_min"]) / res) * res + config["lat_min"]
        snapped_lon = round((lon_val - config["lon_min"]) / res) * res + config["lon_min"]

        # Ensure snapped stays within bounds
        snapped_lat = min(max(snapped_lat, config["lat_min"]), config["lat_max"])
        snapped_lon = min(max(snapped_lon, config["lon_min"]), config["lon_max"])

        # -------------------------------
        # 3️⃣ FIND NEAREST (FLOAT SAFE)
        # -------------------------------

        clean_df["distance"] = (
            (clean_df["lat"] - snapped_lat) ** 2 +
            (clean_df["lon"] - snapped_lon) ** 2
        )

        nearest_row = clean_df.loc[clean_df["distance"].idxmin()]
        value = nearest_row[value_column]

        # -------------------------------
        # DISPLAY
        # -------------------------------

        st.success("Grid Value Found")

        col1, col2 = st.columns(2)

        with col1:
            st.write("Requested Lat:", lat_val)
            st.write("Requested Lon:", lon_val)
            st.write("Snapped Lat:", snapped_lat)
            st.write("Snapped Lon:", snapped_lon)

        with col2:
            st.write("Date:", selected_date.date())
            st.write("Resolution:", f"{res}°")
            st.write("Nearest Grid Lat:", nearest_row["lat"])
            st.write("Nearest Grid Lon:", nearest_row["lon"])
            st.write("Value:", value)

    except ValueError:
        st.error("Latitude and Longitude must be numeric.")

else:
    st.info("Enter latitude and longitude to fetch data.")
