import streamlit as st
import pandas as pd
import os
import glob

st.set_page_config(layout="wide")
st.title("IMD Grid Climate Dashboard")

# ======================================================
# SIDEBAR FILTERS
# ======================================================

st.sidebar.header("Filters")

# Parameter selection
parameter = st.sidebar.selectbox(
    "Select Parameter",
    ["rainfall", "tmax", "tmin"]
)

# Year selection (extract from folder filenames)
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

# Date picker
selected_date = st.sidebar.date_input("Select Date")

# Lat/Lon input
lat_input = st.sidebar.text_input("Enter Latitude")
lon_input = st.sidebar.text_input("Enter Longitude")

# ======================================================
# LOAD SELECTED YEAR DATA ONLY
# ======================================================

@st.cache_data
def load_year_data(parameter, year):

    file_path = os.path.join("data", parameter, f"{year}_{parameter[:-4] if parameter != 'rainfall' else 'rain'}.parquet")

    # fallback if naming simple like 1993_rain.parquet
    if not os.path.exists(file_path):
        possible = glob.glob(os.path.join("data", parameter, f"{year}*.parquet"))
        if possible:
            file_path = possible[0]
        else:
            return None

    df = pd.read_parquet(file_path)

    df.columns = df.columns.str.lower()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df


df = load_year_data(parameter, selected_year)

if df is None:
    st.error("Could not load selected year file.")
    st.stop()

# ======================================================
# FILTER DATA
# ======================================================

if lat_input and lon_input:

    try:
        lat_val = float(lat_input)
        lon_val = float(lon_input)

        filtered = df[
            (df["date"] == pd.to_datetime(selected_date)) &
            (df["lat"] == lat_val) &
            (df["lon"] == lon_val)
        ]

        if filtered.empty:
            st.warning("No data found for this lat-lon-date combination.")
        else:
            value_column = {
                "rainfall": "rain",
                "tmax": "tmax",
                "tmin": "tmin"
            }.get(parameter, "rain")

            if value_column not in filtered.columns:
                st.error(f"{value_column} column not found.")
            else:
                value = filtered.iloc[0][value_column]

                st.success("Data Found")
                st.write("Parameter:", parameter)
                st.write("Year:", selected_year)
                st.write("Date:", selected_date)
                st.write("Latitude:", lat_val)
                st.write("Longitude:", lon_val)
                st.write("Value:", value)

    except ValueError:
        st.error("Latitude and Longitude must be numeric.")

else:
    st.info("Enter latitude and longitude to fetch data.")
