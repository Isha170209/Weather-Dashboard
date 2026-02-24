import streamlit as st
import pandas as pd
import os
import glob
import numpy as np

st.set_page_config(layout="wide")
st.title("IMD Grid Climate Dashboard")

# ================= GRID CONFIG =================
GRID_CONFIG = {
    "rain": {
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

# ================= SIDEBAR =================
st.sidebar.header("Filters")

parameter = st.sidebar.selectbox("Select Parameter", ["rain", "tmax", "tmin"])
config = GRID_CONFIG[parameter]

data_folder = os.path.join("data", parameter)
parquet_files = glob.glob(os.path.join(data_folder, "*.parquet"))

if not parquet_files:
    st.error("No parquet files found.")
    st.stop()

years = sorted([os.path.basename(f).split("_")[0] for f in parquet_files])
selected_year = st.sidebar.selectbox("Select Year", years)

# ================= LOAD DATA =================
@st.cache_data
def load_year_data(parameter, year):
    file = glob.glob(os.path.join("data", parameter, f"{year}*.parquet"))[0]
    df = pd.read_parquet(file)
    df["date"] = pd.to_datetime(df["date"])
    df["lat"] = pd.to_numeric(df["lat"])
    df["lon"] = pd.to_numeric(df["lon"])
    return df

df = load_year_data(parameter, selected_year)

# ================= DATE =================
min_date = df["date"].min()
max_date = df["date"].max()
selected_date = st.sidebar.date_input("Select Date", value=min_date, min_value=min_date, max_value=max_date)

# ================= LAT LON INPUT =================
lat_input = st.sidebar.text_input("Enter Latitude")
lon_input = st.sidebar.text_input("Enter Longitude")

# ================= MAIN LOGIC =================
if lat_input and lon_input:
    try:
        lat_val = float(lat_input)
        lon_val = float(lon_input)

        # ---- Bounds Check ----
        if not (config["lat_min"] <= lat_val <= config["lat_max"]):
            st.error("Latitude outside IMD bounds.")
            st.stop()
        if not (config["lon_min"] <= lon_val <= config["lon_max"]):
            st.error("Longitude outside IMD bounds.")
            st.stop()

        # ---- Resolution Check ----
        res = config["resolution"]
        if round((lat_val - config["lat_min"]) % res, 6) != 0:
            st.error(f"Latitude must be on {res}° grid.")
            st.stop()
        if round((lon_val - config["lon_min"]) % res, 6) != 0:
            st.error(f"Longitude must be on {res}° grid.")
            st.stop()

        selected_date = pd.to_datetime(selected_date)
        date_filtered = df[df["date"] == selected_date]

        if date_filtered.empty:
            st.warning("No data for selected date.")
            st.stop()

        # ---- Exact Match with Tolerance ----
        epsilon = 1e-6  # small tolerance for floating point
        row = date_filtered[
            (np.abs(date_filtered["lat"] - lat_val) < epsilon) &
            (np.abs(date_filtered["lon"] - lon_val) < epsilon)
        ]

        if row.empty:
            st.error("Exact grid point not found in dataset.")
            st.stop()

        value = row.iloc[0][parameter]

        # ---- Display ----
        st.success("Exact Grid Point Found")
        col1, col2 = st.columns(2)
        with col1:
            st.write("Latitude:", lat_val)
            st.write("Longitude:", lon_val)
            st.write("Resolution:", f"{res}°")
        with col2:
            st.write("Date:", selected_date.date())
            st.write("Value:", value)

    except ValueError:
        st.error("Latitude and Longitude must be numeric.")

else:
    st.info("Enter latitude and longitude to fetch data.")
