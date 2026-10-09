"""Streamlit facilities incident management dashboard with automatic data refresh."""

import json
import os
from typing import Any

import streamlit as st

from Data_Manager import (
    update_incident_status,
    delete_incident_by_id,
    export_incidents_to_csv,
    export_incidents_to_txt,
    get_data_dir,
    get_db_path,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = get_db_path()
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


def set_flash(kind: str, message: str) -> None:
    """Keep operation feedback available after a fragment rerun."""
    st.session_state["flash"] = (kind, message)


def load_incidents() -> list[dict[str, Any]] | None:
    """Read the shared JSON database; display errors rather than crashing."""
    if not os.path.exists(DATA_FILE):
        st.warning("No incident database found yet. Submit a report in the terminal to create it.")
        return None

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            records = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        st.error(f"Unable to read the incident database: {error}")
        return None

    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        st.error("The incident database must contain a list of incident records.")
        return None

    return records


def export_and_offer_download(export_fn, filename: str, label: str, mime: str) -> None:
    """Export all incidents and keep the download available after reruns."""
    if not export_fn(filename):
        st.error(f"{label} export failed. Check that the database contains incidents.")
        return

    file_path = os.path.join(get_data_dir(), filename)
    try:
        with open(file_path, "rb") as file:
            data = file.read()
    except OSError as error:
        st.error(f"Unable to open exported {label} report: {error}")
        return

    st.session_state[f"export_data_{label}"] = data
    st.success(f"{label} report generated successfully.")


@st.fragment(run_every="2s")
def incident_dashboard() -> None:
    """Refresh the dashboard from disk so terminal changes appear automatically."""
    flash = st.session_state.pop("flash", None)
    if flash:
        kind, message = flash
        if kind == "success":
            st.success(message)
        else:
            st.error(message)

    incidents = load_incidents()
    if incidents is None:
        return
    if not incidents:
        st.info("No incidents to show yet. New reports will appear automatically.")
        return

    # Highest priority first
    incidents = sorted(incidents, key=lambda item: item.get("priority_score") or 0, reverse=True)

    # ---- Incident table ----
    st.subheader(f"Incidents ({len(incidents)})")
    st.dataframe(
        [
            {
                "ID": item.get("incident_id"),
                "Reported": item.get("timestamp"),
                "Location": item.get("location"),
                "Asset": item.get("asset_info"),
                "Category": item.get("category"),
                "Severity": item.get("severity"),
                "Priority": item.get("final_priority"),
                "Score": item.get("priority_score"),
                "Status": item.get("status"),
            }
            for item in incidents
        ],
        hide_index=False,
        width="stretch",
    )

    # ---- Export ----
    st.markdown("### Export incidents")
    csv_col, txt_col = st.columns(2)
    with csv_col:
        if st.button("Export to CSV", key="export_csv"):
            export_and_offer_download(export_incidents_to_csv, CSV_FILENAME, "CSV", "text/csv")
        if st.session_state.get("export_data_CSV") is not None:
            st.download_button(
                f"Download {CSV_FILENAME}",
                data=st.session_state["export_data_CSV"],
                file_name=CSV_FILENAME,
                mime="text/csv",
                key="download_csv",
            )

    with txt_col:
        if st.button("Export to TXT", key="export_txt"):
            export_and_offer_download(export_incidents_to_txt, TXT_FILENAME, "TXT", "text/plain")
        if st.session_state.get("export_data_TXT") is not None:
            st.download_button(
                f"Download {TXT_FILENAME}",
                data=st.session_state["export_data_TXT"],
                file_name=TXT_FILENAME,
                mime="text/plain",
                key="download_txt",
            )

    st.divider()

    # ---- Incident picker ----
    incidents_by_id = {
        item.get("incident_id"): item
        for item in incidents
        if item.get("incident_id")
    }
    if not incidents_by_id:
        st.warning("No incidents with valid IDs are available to manage.")
        return

    def format_incident_label(incident_id: str) -> str:
        item = incidents_by_id[incident_id]
        asset = item.get("asset_info", "")
        priority = item.get("final_priority", "")
        score = item.get("priority_score", "-")
        return f"{incident_id} — {asset} ({priority}, score {score})"

    if st.session_state.get("selected_incident_id") not in incidents_by_id:
        st.session_state.pop("selected_incident_id", None)

    st.markdown("### Select an incident to view")
    selected_id = st.selectbox(
        "Select an incident to view",
        list(incidents_by_id),
        format_func=format_incident_label,
        key="selected_incident_id",
        label_visibility="collapsed",
    )
    incident = incidents_by_id[selected_id]
    incident_id = incident["incident_id"]

    # ---- Incident detail ----
    st.subheader(f"{incident_id} · {incident.get('asset_info', '')}")
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
        st.markdown(
            f"**Reporter:** {incident.get('reporter_name', '-')} "
            f"({incident.get('reporter_contact', '-')})"
        )
        st.markdown(f"**People affected:** {incident.get('impact_headcount', '-')}")
        st.markdown(f"**Duplicate:** {incident.get('is_duplicate', '-')}")
        st.markdown(f"**Historical frequency:** {incident.get('historical_frequency', '-')}")
        st.markdown(f"**Recommended action:** {incident.get('recommended_action', '-')}")
        st.markdown(f"**Assigned route:** {incident.get('assigned_route', '-')}")
        st.markdown(f"**Escalation reason:** {incident.get('escalation_reason', '-')}")
        st.markdown(f"**Assessment source:** {incident.get('assessment_source', '-')}")
        st.markdown("**Description**")
        st.info(incident.get("description") or "-")

        st.markdown("**AI risk summary**")
        risk_summary = incident.get("risk_summary")
        bullets = []
        if isinstance(risk_summary, str) and risk_summary.strip() and risk_summary.lower() != "none":
            bullets = [line.strip().lstrip("•-*").strip() for line in risk_summary.splitlines()]
            bullets = [item for item in bullets if item]
        st.info("\n".join(f"- {item}" for item in bullets) if bullets else "No risk summary available.")

        st.markdown("**AI contextual insights**")
        st.info(incident.get("contextual_insights") or "No insights available.")

    with right:
        image_path = incident.get("image_path")
        if image_path:
            full_image_path = (
                image_path if os.path.isabs(image_path)
                else os.path.join(BASE_DIR, image_path)
            )
            if os.path.isfile(full_image_path):
                st.image(full_image_path, caption="Visual evidence")
            else:
                st.caption("Visual evidence file not found.")
        else:
            st.caption("No visual evidence provided.")

    # ---- Manage incident ----
    st.divider()
    st.markdown("### Manage incident")
    status_col, delete_col = st.columns(2)

    with status_col:
        st.markdown("**Update status**")
        current_status = incident.get("status") or STATUS_OPTIONS[0]
        status_choices = (
            STATUS_OPTIONS if current_status in STATUS_OPTIONS
            else [current_status] + STATUS_OPTIONS
        )
        new_status = st.selectbox(
            "New status",
            status_choices,
            index=status_choices.index(current_status),
            key=f"status_{incident_id}",
        )
        if st.button(
            "Update status",
            key=f"update_{incident_id}",
            disabled=new_status == current_status,
        ):
            if update_incident_status(incident_id, new_status):
                set_flash("success", f"{incident_id} status changed from '{current_status}' to '{new_status}'.")
            else:
                set_flash("error", f"Couldn't update {incident_id}. Check the database file.")
            st.rerun(scope="fragment")

    with delete_col:
        st.markdown("**Delete incident**")
        confirm_delete = st.checkbox(
            f"I understand {incident_id} will be permanently deleted",
            key=f"confirm_delete_{incident_id}",
        )
        if st.button(
            "Delete incident",
            type="primary",
            key=f"delete_{incident_id}",
            disabled=not confirm_delete,
        ):
            if delete_incident_by_id(incident_id):
                set_flash("success", f"{incident_id} was deleted.")
            else:
                set_flash("error", f"Couldn't delete {incident_id}. It may already be gone.")
            st.rerun(scope="fragment")


incident_dashboard()