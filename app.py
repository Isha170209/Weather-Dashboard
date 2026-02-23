import streamlit as st
import pandas as pd
import os
import json
import requests
import plotly.express as px

st.set_page_config(layout="wide")

# ------------------------------------------------
# HEADER (IMD STYLE)
# ------------------------------------------------

st.markdown("""
    <div style="
        background-color: #E31F26;
        padding: 18px;
    ">
        <h1 style="
            color: white;
            text-align: center;
            margin: 0;
            font-weight: 600;
        ">
            IMD Weather Dashboard
        </h1>
    </div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------
# CACHE: LOAD GEOJSON FROM GOOGLE DRIVE
# ------------------------------------------------

@st.cache_data
def load_boundary():

    # 🔴 Replace with your actual file ID
    FILE_ID = "1NTEbpnCmcsyFS4L0hYYvoyo6uPxeDVJN"

    url = f"https://drive.google.com/uc?export=download&id=1NTEbpnCmcsyFS4L0hYYvoyo6uPxeDVJN"

    response = requests.get(url)
    geojson = response.json()

    # Normalize property names and values
    for feature in geojson["features"]:
        feature["properties"] = {
            k.lower(): v for k, v in feature["properties"].items()
        }

        if "tehsil" in feature["properties"]:
            feature["properties"]["tehsil"] = (
                str(feature["properties"]["tehsil"])
                .strip()
                .lower()
            )

    return geojson


# ------------------------------------------------
# CACHE: LOAD PARQUET FILES
# ------------------------------------------------

@st.cache_data
def load_all_parquet(folder_path):
    files = [f for f in os.listdir(folder_path) if f.endswith(".parquet")]

    if not files:
        return None

    df_list = []
    for f in files:
        df = pd.read_parquet(os.path.join(folder_path, f))
        df_list.append(df)

    df = pd.concat(df_list, ignore_index=True)

    df.columns = df.columns.str.lower()

    # Normalize admin names
    for col in ["state", "district", "tehsil"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()

    return df


# ------------------------------------------------
# LAYOUT
# ------------------------------------------------

left_panel, map_panel = st.columns([1, 3])

# ------------------------------------------------
# FILTER PANEL
# ------------------------------------------------

with left_panel:

    st.markdown("### Filters")

    parameter = st.selectbox("Parameter", ["rain", "tmax", "tmin"])
    folder_path = f"data/{parameter}"

    if not os.path.exists(folder_path):
        st.error("Data folder not found.")
        st.stop()

    df = load_all_parquet(folder_path)

    if df is None:
        st.error("No parquet files found.")
        st.stop()

    required_cols = ["date", "state", "district", "tehsil"]
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        st.error(f"Missing required columns: {missing}")
        st.stop()

    df["date"] = pd.to_datetime(df["date"])

    # STATE
    state = st.selectbox(
        "State",
        sorted(df["state"].dropna().unique())
    )

    df_state = df[df["state"] == state]

    # DISTRICT
    district = st.selectbox(
        "District",
        sorted(df_state["district"].dropna().unique())
    )

    df_district = df_state[df_state["district"] == district]

    # TEHSIL
    tehsil = st.selectbox(
        "Tehsil",
        sorted(df_district["tehsil"].dropna().unique())
    )

    df_tehsil = df_district[df_district["tehsil"] == tehsil]

    # DATE RANGE
    min_date = df["date"].min()
    max_date = df["date"].max()

    start_date = st.date_input(
        "Start Date",
        min_value=min_date,
        max_value=max_date,
        value=min_date
    )

    end_date = st.date_input(
        "End Date",
        min_value=min_date,
        max_value=max_date,
        value=max_date
    )

    col1, col2 = st.columns(2)
    confirm = col1.button("Confirm")
    reset = col2.button("Reset")

    if reset:
        st.experimental_rerun()


# ------------------------------------------------
# MAP PANEL
# ------------------------------------------------

with map_panel:

    if confirm:

        df_filtered = df_tehsil[
            (df_tehsil["date"] >= pd.to_datetime(start_date)) &
            (df_tehsil["date"] <= pd.to_datetime(end_date))
        ]

        if df_filtered.empty:
            st.warning("No data available for selected filters.")
            st.stop()

        non_value_cols = ["date", "lat", "lon", "state", "district", "tehsil"]
        value_columns = [col for col in df.columns if col not in non_value_cols]

        if not value_columns:
            st.error("No climate value column found.")
            st.stop()

        value_column = value_columns[0]

        agg = (
            df_filtered
            .groupby("tehsil")[value_column]
            .mean()
            .reset_index()
        )

        geojson = load_boundary()

        fig = px.choropleth_mapbox(
            agg,
            geojson=geojson,
            locations="tehsil",
            featureidkey="properties.tehsil",
            color=value_column,
            mapbox_style="carto-positron",
            zoom=5,
            center={"lat": 22.5, "lon": 80},
            opacity=0.75
        )

        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Select filters and click Confirm to display the map.")
