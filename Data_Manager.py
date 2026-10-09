
"""
INF1103 Team 4
Campus Safety Hazard Reporting System

DATA MANAGER

Handles:
1. Incident database storage
2. AI assessment database storage
3. Incident ID generation
4. Searching and updating incidents
5. Deleting and clearing incidents
6. Exporting incidents to CSV

All JSON reading and writing happens in this module.
"""

import os
import json
import csv
import logging
from datetime import datetime
from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILENAME = "hazardreportdb.json"
AI_DB_FILENAME = "ai_assessments.json"

last_load_warning = ""


def get_data_dir() -> str:
    """
    Returns the database directory.
    """

    custom_dir = os.getenv("HAZARD_DATA_DIR")

    if custom_dir:
        return os.path.abspath(custom_dir)

    return BASE_DIR


def get_db_path() -> str:
    """
    Returns the incident database path.
    """

    custom_path = os.getenv("INCIDENTS_DB")

    if custom_path:
        return os.path.abspath(custom_path)

    return os.path.join(
        get_data_dir(),
        DB_FILENAME
    )


def get_ai_db_path() -> str:
    """
    Returns the AI assessment database path.
    """

    return os.path.join(
        get_data_dir(),
        AI_DB_FILENAME
    )


# ============================================================
# READ JSON DATABASE
# ============================================================

def read_json(file_path: str) -> list[dict[str, Any]]:
    """
    Reads a JSON database containing a list of records.

    Missing file: returns an empty list.
    Invalid file: raises an error.
    """

    if not os.path.exists(file_path):
        return []

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError(
            f"Database must contain a list: {file_path}"
        )

    if not all(isinstance(item, dict) for item in records):
        raise ValueError(
            f"Database contains invalid records: {file_path}"
        )

    return records


# ============================================================
# WRITE JSON DATABASE
# ============================================================

def write_json(
    file_path: str,
    records: list[dict[str, Any]]
) -> bool:
    """
    Writes records through a temporary file.

    This reduces the chance of leaving a partially
    written JSON database if writing fails.
    """

    temp_path = file_path + ".tmp"

    try:
        os.makedirs(
            os.path.dirname(os.path.abspath(file_path)),
            exist_ok=True
        )

        with open(
            temp_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                records,
                file,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temp_path, file_path)

        return True

    except (OSError, TypeError, ValueError) as error:
        logger.error(
            "Failed to write database %s: %s",
            file_path,
            error
        )
        return False


# ============================================================
# LOAD INCIDENTS
# ============================================================

def load() -> list[dict[str, Any]]:
    """
    Loads incident records from hazardreportdb.json.
    """

    global last_load_warning

    last_load_warning = ""

    try:
        return read_json(get_db_path())

    except (
        OSError,
        json.JSONDecodeError,
        ValueError
    ) as error:

        last_load_warning = (
            f"Unable to load incident database: {error}"
        )

        logger.error(last_load_warning)

        return []


# ============================================================
# GENERATE INCIDENT ID
# ============================================================

def generate_incident_id(
    records: list[dict[str, Any]]
) -> str:
    """
    Generates the next incident ID.

    Also checks AI assessment IDs so an incident ID
    is not reused while an older AI assessment exists.
    """

    highest_id = 0

    for record in records:
        incident_id = str(record.get("incident_id", ""))

        if incident_id.startswith("INCIDENT-"):
            number = incident_id[len("INCIDENT-"):]

            if number.isdigit():
                highest_id = max(highest_id, int(number))

    # Include IDs from previous AI assessments
    ai_records = read_json(get_ai_db_path())

    for assessment in ai_records:
        incident_id = str(
            assessment.get("incident_id", "")
        )

        if incident_id.startswith("INCIDENT-"):
            number = incident_id[len("INCIDENT-"):]

            if number.isdigit():
                highest_id = max(highest_id, int(number))

    return f"INCIDENT-{highest_id + 1:03d}"


# ============================================================
# SAVE INCIDENT
# ============================================================

def save(record: dict[str, Any]) -> bool:
    """
    Saves a new incident into hazardreportdb.json.

    Assigns an incident ID and timestamp.
    """

    if not isinstance(record, dict):
        logger.error("Invalid incident record.")
        return False

    records = load()

    if last_load_warning:
        logger.error(
            "Incident save cancelled due to database error."
        )
        return False

    try:
        if not record.get("incident_id"):
            record["incident_id"] = generate_incident_id(
                records
            )

    except (
        OSError,
        json.JSONDecodeError,
        ValueError
    ) as error:
        logger.error(
            "Unable to generate incident ID: %s",
            error
        )
        return False

    if not record.get("timestamp"):
        record["timestamp"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    if not record.get("status"):
        record["status"] = "Pending Review"

    for existing in records:
        if existing.get("incident_id") == record["incident_id"]:
            logger.error(
                "Duplicate incident ID: %s",
                record["incident_id"]
            )
            return False

    records.append(record)

    return write_json(get_db_path(), records)


# ============================================================
# SAVE AI ASSESSMENT
# ============================================================

def save_ai_assessment(
    record: dict[str, Any],
    ai_result: dict[str, Any],
    assessment_source: str
) -> bool:
    """
    Saves AI assessment data to ai_assessments.json.

    The AI assessment is linked to the original
    incident through its incident_id.
    """

    if not isinstance(record, dict):
        logger.error("Invalid incident record.")
        return False

    if not isinstance(ai_result, dict):
        logger.error("Invalid AI assessment.")
        return False

    incident_id = record.get("incident_id")

    if not incident_id:
        logger.error(
            "Cannot save AI assessment without incident ID."
        )
        return False

    # Load existing AI assessments
    try:
        assessments = read_json(get_ai_db_path())

    except (
        OSError,
        json.JSONDecodeError,
        ValueError
    ) as error:
        logger.error(
            "Unable to load AI assessments: %s",
            error
        )
        return False

    # Prevent duplicate assessment IDs
    for existing in assessments:
        if existing.get("incident_id") == incident_id:
            logger.error(
                "AI assessment already exists for %s",
                incident_id
            )
            return False

    # Prepare assessment record
    assessment = {
        "incident_id": incident_id,
        "timestamp": record.get("timestamp"),
        "reporter_name": record.get("reporter_name"),
        "location": record.get("location"),
        "asset_info": record.get("asset_info"),
        "description": record.get("description"),
        "assessment_source": assessment_source,
        "risk_summary": ai_result.get("risk_summary"),
        "category": ai_result.get("category"),
        "severity": ai_result.get("severity"),
        "operational_impact": ai_result.get(
            "operational_impact"
        ),
        "contextual_insights": ai_result.get(
            "contextual_insights"
        ),
        "historical_frequency": record.get(
            "historical_frequency"
        ),
        "priority_score": record.get(
            "priority_score"
        ),
        "final_priority": record.get(
            "final_priority"
        ),
        "recommended_action": record.get(
            "recommended_action"
        ),
        "escalation_reason": record.get(
            "escalation_reason"
        ),
        "assigned_route": record.get(
            "assigned_route"
        ),
        "is_duplicate": record.get(
            "is_duplicate"
        )
    }

    assessments.append(assessment)

    return write_json(
        get_ai_db_path(),
        assessments
    )


# ============================================================
# QUERY INCIDENTS
# ============================================================

def query(filter_fn) -> list[dict[str, Any]]:
    """
    Filters incidents using a function.

    Example:
        query(lambda r: r.get("status") == "Pending Review")
    """

    records = load()

    if last_load_warning:
        return []

    if not callable(filter_fn):
        logger.error("query() requires a filter function.")
        return []

    return [
        record
        for record in records
        if filter_fn(record)
    ]


# ============================================================
# UPDATE INCIDENT STATUS
# ============================================================

def update_incident_status(
    incident_id: str,
    new_status: str
) -> bool:
    """
    Updates an incident's status.
    """

    records = load()

    if last_load_warning:
        return False

    for record in records:
        if record.get("incident_id") == incident_id:
            record["status"] = new_status

            return write_json(
                get_db_path(),
                records
            )

    return False


# ============================================================
# DELETE INCIDENT
# ============================================================

def delete_incident_by_id(
    incident_id: str
) -> bool:
    """
    Deletes an incident by ID.

    Existing AI assessments are preserved.
    """

    records = load()

    if last_load_warning:
        return False

    updated_records = [
        record
        for record in records
        if record.get("incident_id") != incident_id
    ]

    if len(updated_records) == len(records):
        return False

    return write_json(
        get_db_path(),
        updated_records
    )


# ============================================================
# CLEAR INCIDENT DATABASE
# ============================================================

def clear_database() -> bool:
    """
    Clears the incident database.

    AI assessment records are not deleted.
    """

    records = load()

    if last_load_warning:
        return False

    return write_json(
        get_db_path(),
        []
    )


# ============================================================
# EXPORT INCIDENTS TO CSV
# ============================================================

def export_incidents_to_csv(
    filename: str = "hazard_reports.csv"
) -> bool:
    """
    Exports all incident records to CSV.
    """

    records = load()

    if last_load_warning or not records:
        return False

    fieldnames = []

    for record in records:
        for key in record.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    file_path = os.path.join(
        get_data_dir(),
        filename
    )

    try:
        os.makedirs(
            os.path.dirname(os.path.abspath(file_path)),
            exist_ok=True
        )

        with open(
            file_path,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames
            )

            writer.writeheader()
            writer.writerows(records)

        return True

    except (OSError, ValueError) as error:
        logger.error(
            "CSV export failed: %s",
            error
        )
        return False


# ============================================================
# COMPATIBILITY FUNCTION
# ============================================================

def export_incidents_to_txt(
    filename: str = "hazard_reports.csv"
) -> bool:
    """
    Compatibility wrapper for older integrations.

    Exports CSV data using the supplied filename.
    """

    return export_incidents_to_csv(filename)
