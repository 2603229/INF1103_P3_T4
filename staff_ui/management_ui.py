import json
import os
import streamlit as st

DATA_FILE = "incidents.json"

st.set_page_config(page_title="Incident Management", layout="wide")
st.title("Facilities incident management")

# ---- Load data ----
if not os.path.exists(DATA_FILE):
    st.error(f"Couldn't find {DATA_FILE}. Put it in the same folder as this file.")
    st.stop()

with open(DATA_FILE, "r", encoding="utf-8") as f:
    incidents = json.load(f)

if not incidents:
    st.info("No incidents to show yet.")
    st.stop()

# ---- Incident table ----
st.subheader(f"Incidents ({len(incidents)})")
st.dataframe(
    [
        {
            "ID": i.get("incident_id"),
            "Reported": i.get("timestamp"),
            "Location": i.get("location"),
            "Asset": i.get("asset_info"),
            "Category": i.get("category"),
            "Severity": i.get("severity"),
            "Priority": i.get("final_priority"),
            "Score": i.get("priority_score"),
            "Status": i.get("status"),
        }
        for i in incidents
    ],
    hide_index=False,
    width="stretch",
)