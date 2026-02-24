import streamlit as st
import pandas as pd
import os
import glob
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("Weather Data Dashboard")

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

# Parameter selection
parameter = st.sidebar.selectbox("Select Parameter", ["rain", "tmax", "tmin"])
config = GRID_CONFIG[parameter]

# Load ALL parquet files for selected parameter
@st.cache_data
def load_all_data(parameter):
    folder = os.path.join("data", parameter)
    files = glob.glob(os.path.join(folder, "*.parquet"))
    if not files:
        return None
    df_list = []
    for f in files:
        temp = pd.read_parquet(f)
        df_list.append(temp)
    df = pd.concat(df_list, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df["lat"] = pd.to_numeric(df["lat"])
    df["lon"] = pd.to_numeric(df["lon"])
    return df

df = load_all_data(parameter)

if df is None:
    st.error("No parquet files found.")
    st.stop()

# Date Range Filters
min_date = df["date"].min()
max_date = df["date"].max()

start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("End Date", max_date, min_value=min_date, max_value=max_date)

# Lat/Lon input
lat_input = st.sidebar.text_input("Enter Latitude")
lon_input = st.sidebar.text_input("Enter Longitude")

submit_button = st.sidebar.button("Submit")

# ================= MAIN LOGIC =================
if submit_button:

    if not lat_input or not lon_input:
        st.warning("Please enter both latitude and longitude.")
        st.stop()

    try:
        lat_val = float(lat_input)
        lon_val = float(lon_input)

        # Bounds check
        if not (config["lat_min"] <= lat_val <= config["lat_max"]):
            st.error("Latitude outside IMD bounds.")
            st.stop()

        if not (config["lon_min"] <= lon_val <= config["lon_max"]):
            st.error("Longitude outside IMD bounds.")
            st.stop()

        # Date range validation
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

        if start_date > end_date:
            st.error("Start Date cannot be after End Date.")
            st.stop()

        # Filter by date range
        date_filtered = df[
            (df["date"] >= start_date) &
            (df["date"] <= end_date)
        ]

        if date_filtered.empty:
            st.warning("No data in selected date range.")
            st.stop()

        # Exact grid match
        epsilon = 1e-6
        grid_filtered = date_filtered[
            (np.abs(date_filtered["lat"] - lat_val) < epsilon) &
            (np.abs(date_filtered["lon"] - lon_val) < epsilon)
        ].sort_values("date")

        if grid_filtered.empty:
            st.error("Exact grid point not found in dataset.")
            st.stop()

        # ================= TABS =================
        tab1, tab2, tab3 = st.tabs(["Description", "Tabular", "Graphical"])

        # ---------- DESCRIPTION ----------
        with tab1:
            st.success("Grid Point Found")

            col1, col2 = st.columns(2)

            with col1:
                st.write("Latitude:", lat_val)
                st.write("Longitude:", lon_val)
                st.write("Resolution:", f"{config['resolution']}°")

            with col2:
                st.write("Start Date:", start_date.date())
                st.write("End Date:", end_date.date())
                st.write("Mean Value:", round(grid_filtered[parameter].mean(), 2))
                st.write("Min Value:", round(grid_filtered[parameter].min(), 2))
                st.write("Max Value:", round(grid_filtered[parameter].max(), 2))

        # ---------- TABULAR ----------
        with tab2:
            st.subheader("Filtered Data (Selected Date Range)")
            st.dataframe(grid_filtered, use_container_width=True)

            csv = grid_filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"{parameter}_{lat_val}_{lon_val}.csv",
                mime="text/csv"
            )

        # ---------- GRAPHICAL ----------
        with tab3:
            st.subheader("Time Series (Selected Date Range)")

            fig, ax = plt.subplots(figsize=(12, 4))
            ax.plot(grid_filtered["date"], grid_filtered[parameter], marker="o")
            ax.set_xlabel("Date")
            ax.set_ylabel(parameter.capitalize())
            ax.set_title(f"{parameter.capitalize()} from {start_date.date()} to {end_date.date()}")
            ax.grid(True)
            st.pyplot(fig)

    except ValueError:
        st.error("Latitude and Longitude must be numeric.")

else:
    st.info("Select filters and click Submit to fetch data.")
