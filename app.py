import streamlit as st
import pandas as pd
import requests
import json
import plotly.express as px

st.set_page_config(layout="wide")

st.title("IMD Rainfall Dashboard")

# ==============================
# LOAD DATA
# ==============================

import os
import glob

@st.cache_data
def load_data():

    base_path = "data"

    if not os.path.exists(base_path):
        st.error("Data folder not found.")
        st.stop()

    df_list = []

    # Loop through parameter folders
    for parameter_folder in ["rainfall", "tmax", "tmin"]:

        folder_path = os.path.join(base_path, parameter_folder)

        if not os.path.exists(folder_path):
            continue

        parquet_files = glob.glob(os.path.join(folder_path, "*.parquet"))

        for file in parquet_files:
            df = pd.read_parquet(file)

            # Add parameter column manually
            df["parameter"] = parameter_folder

            df_list.append(df)

    if not df_list:
        st.error("No parquet files found in data subfolders.")
        st.stop()

    df = pd.concat(df_list, ignore_index=True)

    # Normalize text columns
    df["state"] = df["state"].str.strip().str.lower()
    df["tehsil"] = df["tehsil"].str.strip().str.lower()
    df["parameter"] = df["parameter"].str.strip().str.lower()

    return df

# ==============================
# STATE FILE IDS (GOOGLE DRIVE)
# ==============================

STATE_FILE_IDS = {
    "andaman_nicobar": "1WoKzWAr6GM89JIYTSw5gYLHjdQPo7DZT",
    "andhra_pradesh": "1AqVtI7-tOVBv5GjpDKPrcWIvoMkQ2vJn",
    "arunchal_pradesh": "1xLLuvJKkSR_1jVTW9SdfLpEs6EXJCb8F",
    "assam": "1QNY5ixe1CS30zBJszM4ItjF8IN7zb6nS",
    "bihar": "1jbz3aErYkOaPdABerus6e-UAaZ_YrCoy",
    "chandigarh": "1a3LaLD39vs61NA6PtqRtoQ0Yln3plm2r",
    "chhattisgarh": "17BIaNHKkQLjOEKQmtFQipd837PUd6mR8",
    "dadra_nagar_haveli_daman_diu": "1Aj7PpBPGBuYCpLXAeb4rJ2EBAwmD_zPy",
    "delhi": "1rSuc5iEJhAropYakUo2TlZC9sLJsVsBK",
    "disputed_westbengal": "1xeAlKgKx74K6FWVxrmBtQsawUniBfQQS",
    "disputed": "1HP1EMtsBMlzWLboptCqSsLlFt2SGEhv5",
    "goa": "1tz_mykI0e2lNSmAAMgHg_r8gHoDWTYVi",
    "gujarat": "1os-EzdYxHirZav7QNoB6jOvZR-O70SVu",
    "haryana": "1giX-ntvwMB9wa5usNR9dIAwZ3HGAJHdG",
    "himachal_pradesh": "1D8Fmi8a3sdz16vEDzm44b9prrI3oC8UB",
    "jammu_kashmir": "1NFfmao42z4xu4bbBodPq3EW3Tz8SJH2Y",
    "jharkhand": "1QFSNYUjDO9QJBEjkjy69OG8vp6BnUCPU",
    "karnataka": "1C4kIGVzfhG8F6ru2zccSJ0xuqEiJAR34",
    "kerala": "1KU42UbqVFRbhd03UIuB_mXn64ZmcJhEL",
    "ladakh": "11JivUTcvJrX1m15pj7e3hyKBbGI4_r0g",
    "lakshadweep": "14ggNRvV840_NhiXAzxNVsssfkpaMjxLr",
    "madhya_pradesh_disputed": "13wiAQTJFlmaceSByYr9p0EHYpCEklwE8",
    "madhya_pradesh": "13PUt6JsHRmOpzutfl2rP6xKYtu10Cqir",
    "maharashtra": "1o1d9nZdHjyIivRpbklGEdQ_dngKLo4es",
    "manipur": "1pYBPwB2PW-IST73Wq-Ca14ulR6GwV9Yg",
    "meghalaya": "16BjIoAPmNhML2PG-XjQnwaILofQkfMmJ",
    "mizoram": "1jz_a_RXj89Yszd5i05Xy59TNNylWFnyU",
    "nagaland": "1GOS5q_6ic2RlF2y-xJBEUqyivjWZrbhR",
    "odisha": "1rVtcpWT1-O-vYmjEzAArKMMXDA1wIYMI",
    "puducherry": "15YLDuy66g3wx8EDVqb6cetbc_aYMhBAR",
    "punjab": "1bO2KAIHXlR2Jlit0a6iDnIZ-gk0xUAJm",
    "rajasthan": "12oTbj7eCIFOv2PkNJw8CP1PeuQs_WIF3",
    "sikkim": "1M-tUqNdUiciWwQWb99N7h3EfcbgkU72f",
    "tamil_nadu": "1y5wnAKByePYT2gpW9bKY5fafpJPtWzxk",
    "telangana": "16cEgosKyvTD481j1KAdzl0zAqrhwDheG",
    "tripura": "1MVlk3CtKXjsX1wqQtjvcqN8SdOnXK1ZR",
    "uttar_pradesh": "1RkNQVQIkidG8Tjiz0SWdPxN6Do1bXMUK",
    "uttarakhand": "1XyXiqPmLJ7bbpJM5PfHcW8eZ571TL8oS",
    "west_bengal": "1F0YnvVXRiU3OJ2hTNKEkBlh179AwiFkm"
}

# ==============================
# LOAD GEOJSON PER STATE
# ==============================

@st.cache_data(show_spinner=False)
def load_boundary(selected_state):
    file_id = STATE_FILE_IDS.get(selected_state)

    if not file_id:
        return None

    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(url, timeout=60)

    if response.status_code != 200:
        return None

    geojson = json.loads(response.content)

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


# ==============================
# SIDEBAR FILTERS
# ==============================

st.sidebar.header("Filters")

state = st.sidebar.selectbox(
    "Select State",
    sorted(df["state"].unique())
)

filtered_df = df[df["state"] == state]

if filtered_df.empty:
    st.warning("No data available for selected state.")
    st.stop()

parameter = st.sidebar.selectbox(
    "Select Parameter",
    filtered_df["parameter"].unique()
)

filtered_df = filtered_df[filtered_df["parameter"] == parameter]

# ==============================
# LOAD MAP
# ==============================

geojson = load_boundary(state)

if geojson is None:
    st.error("Boundary file not found for selected state.")
    st.stop()

fig = px.choropleth(
    filtered_df,
    geojson=geojson,
    locations="tehsil",
    featureidkey="properties.tehsil",
    color="value",
    projection="mercator"
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(height=700)

st.plotly_chart(fig, use_container_width=True)
