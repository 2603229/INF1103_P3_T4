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