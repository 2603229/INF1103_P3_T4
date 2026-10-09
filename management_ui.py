import json
import os
import streamlit as st

from Data_Manager import (
    update_incident_status,
    delete_incident_by_id,
    export_incidents_to_csv,
    export_incidents_to_txt,
    get_data_dir,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.environ.get("INCIDENTS_DB", os.path.join(BASE_DIR, "hazardreportdb.json"))
EMPTY_VALUES = {None, "", "None", "none", "null"}

STATUS_OPTIONS = ["Pending Review", "In Progress", "Resolved", "Closed"]
CSV_FILENAME = "hazard_reports.csv"
TXT_FILENAME = "hazard_reports.txt"

st.set_page_config(page_title="Incident Management", layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stMarkdownContainer"] strong {
        font-size: 1.15rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Facilities incident management")

# ---- Feedback messages that survive st.rerun() ----
def set_flash(kind, message):
    st.session_state["flash"] = (kind, message)


flash = st.session_state.pop("flash", None)
if flash:
    kind, message = flash
    if kind == "success":
        st.success(message)
    else:
        st.error(message)


# ---- Load data ----
if not os.path.exists(DATA_FILE):
    st.error(f"Couldn't find {DATA_FILE}. Put it in the same folder as this file.")
    st.stop()

with open(DATA_FILE, "r", encoding="utf-8") as f:
    incidents = json.load(f)

if not incidents:
    st.info("No incidents to show yet.")
    st.stop()

def get_priority_score(i):
    return i.get("priority_score") or 0

# Highest priority first
def get_priority_score(i):
    return i.get("priority_score") or 0
incidents = sorted(incidents, key=get_priority_score, reverse=True)

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

st.divider()

# ---- Incident picker ----
def format_incident_label(incident):
    incident_id = incident.get("incident_id")
    asset = incident.get("asset_info", "")
    priority = incident.get("final_priority", "")
    score = incident.get("priority_score", "-")
    return f"{incident_id} — {asset} ({priority}, score {score})"

st.markdown("### Select an incident to view")

incident = st.selectbox(
    "Select an incident to view",
    incidents,
    format_func=format_incident_label,
    label_visibility="collapsed",
)

# ---- Incident detail ----
st.subheader(f"{incident['incident_id']} · {incident.get('asset_info', '')}")
left, right = st.columns([3, 2])

with left:
    st.markdown(f"**Status:** {incident.get('status', '-')}")
    st.markdown(
        f"**Severity:** {incident.get('severity', '-')} · "
        f"**Operational impact:** {incident.get('operational_impact', '-')}"
    )
    st.markdown(
        f"**Priority:** {incident.get('final_priority', '-')} "
        f"(score {incident.get('priority_score', '-')})"
    )
    st.markdown(f"**Category:** {incident.get('category', '-')}")
    st.markdown(f"**Location:** {incident.get('location', '-')}")
    st.markdown(f"**Reported:** {incident.get('timestamp', '-')}")
    st.markdown(f"**Reporter:** {incident.get('reporter_name', '-')} ({incident.get('reporter_contact', '-')})")
    st.markdown(f"**People affected:** {incident.get('impact_headcount', '-')}")
    st.markdown(f"**Duplicate:** {incident.get('is_duplicate', '-')}")
    st.markdown(f"**Historical frequency:** {incident.get('historical_frequency', '-')}")
    st.markdown(f"**Recommended action:** {incident.get('recommended_action', '-')}")
    st.markdown(f"**Assigned route:** {incident.get('assigned_route', '-')}")
    st.markdown(f"**Escalation reason:** {incident.get('escalation_reason', '-')}")
    st.markdown(f"**Assessment source:** {incident.get('assessment_source', '-')}")
    st.markdown("**Description**")
    st.info(incident.get("description", "-"))

    # Risk summary uses "•" or "-" bullets on separate lines; render as a markdown list
    st.markdown("**AI risk summary**")
    risk_summary = incident.get("risk_summary")
    bullets = []
    if risk_summary not in EMPTY_VALUES:
        bullets = [line.strip().lstrip("•-*").strip() for line in risk_summary.splitlines()]
        bullets = [b for b in bullets if b]
    st.info("\n".join(f"- {b}" for b in bullets) if bullets else "No risk summary available.")

    st.markdown("**AI contextual insights**")
    st.info(incident.get("contextual_insights") or "No insights available.")

with right:
    image_path = incident.get("image_path")
    if image_path and os.path.isfile(image_path):
        st.image(image_path, caption="Visual evidence")
    else:
        st.caption(f"No image found at: {image_path or 'not provided'}")