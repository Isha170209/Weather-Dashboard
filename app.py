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

# Select parameter
parameter = st.sidebar.selectbox(
    "Select Parameter",
    ["rainfall", "tmax", "tmin"]
)

# Get available parquet files
data_folder = os.path.join("data", parameter)
parquet_files = glob.glob(os.path.join(data_folder, "*.parquet"))

if not parquet_files:
    st.error("No parquet files found.")
    st.stop()

# Extract years from filenames (assumes 1993_rain.parquet etc.)
years = sorted([
    os.path.basename(f).split("_")[0]
    for f in parquet_files
])

selected_year = st.sidebar.selectbox("Select Year", years)

# Load selected year file
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

# Date range limits
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
# MAIN LOGIC
# ======================================================

if lat_input and lon_input:

    try:
        lat_val = float(lat_input)
        lon_val = float(lon_input)

        selected_date = pd.to_datetime(selected_date)

        # Filter by date
        date_filtered = df[df["date"] == selected_date]

        if date_filtered.empty:
            st.warning("No data available for selected date.")
            st.stop()

        # Identify correct value column
        value_column = {
            "rainfall": "rain",
            "tmax": "tmax",
            "tmin": "tmin"
        }.get(parameter, "rain")

        if value_column not in date_filtered.columns:
            st.error(f"{value_column} column not found in dataset.")
            st.stop()

        # Convert to numeric (Fix Option 3)
        date_filtered["lat"] = pd.to_numeric(date_filtered["lat"], errors="coerce")
        date_filtered["lon"] = pd.to_numeric(date_filtered["lon"], errors="coerce")
        date_filtered[value_column] = pd.to_numeric(
            date_filtered[value_column], errors="coerce"
        )

        # Drop NaNs
        clean_df = date_filtered.dropna(
            subset=["lat", "lon", value_column]
        )

        if clean_df.empty:
            st.error("All values for this date are NaN. Check parquet generation.")
            st.stop()

        # --------------------------------------------------
        # NEAREST NEIGHBOUR
        # --------------------------------------------------

        clean_df["distance"] = (
            (clean_df["lat"] - lat_val) ** 2 +
            (clean_df["lon"] - lon_val) ** 2
        )

        nearest_index = clean_df["distance"].idxmin()
        nearest_row = clean_df.loc[nearest_index]

        value = nearest_row[value_column]

        # --------------------------------------------------
        # DISPLAY RESULTS
        # --------------------------------------------------

        st.success("Nearest Grid Point Found")

        col1, col2 = st.columns(2)

        with col1:
            st.write("Requested Latitude:", lat_val)
            st.write("Requested Longitude:", lon_val)
            st.write("Date:", selected_date.date())
            st.write("Parameter:", parameter)

        with col2:
            st.write("Nearest Grid Latitude:", nearest_row["lat"])
            st.write("Nearest Grid Longitude:", nearest_row["lon"])
            st.write("Value:", value)

        # Optional debug
        # st.write("Rows before cleaning:", len(date_filtered))
        # st.write("Rows after cleaning:", len(clean_df))

    except ValueError:
        st.error("Latitude and Longitude must be numeric.")

else:
    st.info("Enter latitude and longitude to fetch data.")
