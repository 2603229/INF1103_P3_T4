import json
import os
import streamlit as st

DATA_FILE = "incidents.json"

st.set_page_config(page_title="Incident Management", layout="wide")
st.title("Facilities incident management")