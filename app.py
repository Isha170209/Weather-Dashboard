import streamlit as st
import pandas as pd
import os
import glob
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("IMD Weather Data Dashboard")

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

# ================= SIDEBAR FORM =================
st.sidebar.header("Filters")

with st.sidebar.form("filter_form"):

    parameter = st.selectbox("Select Parameter", ["rain", "tmax", "tmin"])
    config = GRID_CONFIG[parameter]

    data_folder = os.path.join("data", parameter)
    parquet_files = glob.glob(os.path.join(data_folder, "*.parquet"))

    if not parquet_files:
        st.error("No parquet files found.")
        st.stop()

    years = sorted([os.path.basename(f).split("_")[0] for f in parquet_files])
    selected_year = st.selectbox("Select Year", years)

    # Load data for date bounds
    @st.cache_data
    def load_year_data(parameter, year):
        file = glob.glob(os.path.join("data", parameter, f"{year}*.parquet"))[0]
        df = pd.read_parquet(file)
        df["date"] = pd.to_datetime(df["date"])
        df["lat"] = pd.to_numeric(df["lat"])
        df["lon"] = pd.to_numeric(df["lon"])
        return df

    df = load_year_data(parameter, selected_year)

    min_date = df["date"].min()
    max_date = df["date"].max()

    selected_date = st.date_input(
        "Select Date",
        value=min_date,
        min_value=min_date,
        max_value=max_date
    )

    lat_input = st.text_input("Enter Latitude")
    lon_input = st.text_input("Enter Longitude")

    submit_button = st.form_submit_button("Submit")
    reset_button = st.form_submit_button("Reset")

# Reset Logic
if reset_button:
    st.experimental_rerun()

# ================= MAIN LOGIC =================
if submit_button:

    if not lat_input or not lon_input:
        st.warning("Please enter both latitude and longitude.")
        st.stop()

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

        selected_date = pd.to_datetime(selected_date)
        date_filtered = df[df["date"] == selected_date]

        if date_filtered.empty:
            st.warning("No data for selected date.")
            st.stop()

        # ---- Exact Match with tolerance ----
        epsilon = 1e-6
        row = date_filtered[
            (np.abs(date_filtered["lat"] - lat_val) < epsilon) &
            (np.abs(date_filtered["lon"] - lon_val) < epsilon)
        ]

        if row.empty:
            st.error("Exact grid point not found in dataset.")
            st.stop()

        value = row.iloc[0][parameter]

        # Get full time series for selected grid
        all_data = df[
            (np.abs(df["lat"] - lat_val) < epsilon) &
            (np.abs(df["lon"] - lon_val) < epsilon)
        ].sort_values("date")

        # ================= TABS =================
        tab1, tab2, tab3 = st.tabs(["Description", "Tabular", "Graphical"])

        # ---------- DESCRIPTION ----------
        with tab1:
            st.success("Exact Grid Point Found")

            col1, col2 = st.columns(2)

            with col1:
                st.write("Latitude:", lat_val)
                st.write("Longitude:", lon_val)
                st.write("Resolution:", f"{config['resolution']}°")

            with col2:
                st.write("Date:", selected_date.date())
                st.write("Value:", value)

        # ---------- TABULAR ----------
        with tab2:
            st.subheader("Tabular Data")

            if all_data.empty:
                st.warning("No historical data for this grid point.")
            else:
                st.dataframe(all_data, use_container_width=True)

                csv = all_data.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{parameter}_{lat_val}_{lon_val}.csv",
                    mime="text/csv"
                )

        # ---------- GRAPHICAL ----------
        with tab3:
            st.subheader("Graphical Data")

            if all_data.empty:
                st.warning("No historical data to plot.")
            else:
                fig, ax = plt.subplots(figsize=(12, 4))
                ax.plot(all_data["date"], all_data[parameter])
                ax.set_xlabel("Date")
                ax.set_ylabel(parameter.capitalize())
                ax.set_title(f"{parameter.capitalize()} Time Series ({lat_val}, {lon_val})")
                ax.grid(True)
                st.pyplot(fig)

    except ValueError:
        st.error("Latitude and Longitude must be numeric.")

else:
    st.info("Fill the filters in sidebar and click Submit to fetch data.")
