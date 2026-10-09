"""
INF1103 Team 4
Campus Safety Hazard Reporting System

DATA MANAGER

Handles:
1. Incident database storage (hazardreportdb.json)
2. Incident ID generation
3. Searching and updating incidents
4. Deleting and clearing incidents
5. Exporting incidents to CSV

Every incident is stored as ONE complete record containing:
    - the reporter's input,
    - the AI assessment (Gemini or offline fallback),
    - the priority and routing decision.

hazardreportdb.json is the single database for the system.
All JSON reading and writing happens in this module.
"""

import os
import json
import csv
import logging
from datetime import datetime
from typing import Any, Callable, Optional


# ============================================================
# CONFIGURATION
# ============================================================

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILENAME = "hazardreportdb.json"

last_load_warning = ""

# Complete schema of a stored incident, in the order fields
# appear in hazardreportdb.json. Every new record is saved with
# all of these keys so the database has one consistent shape.
RECORD_FIELDS: list[str] = [
    # Identification
    "incident_id",
    "timestamp",
    "status",

    # Reporter input (IO_Manager)
    "reporter_name",
    "reporter_contact",
    "location",
    "impact_headcount",
    "asset_info",
    "description",
    "image_path",

    # AI assessment (ai_manager / offline fallback)
    "assessment_source",
    "category",
    "severity",
    "operational_impact",
    "risk_summary",
    "contextual_insights",

    # Priority and routing decision (logic_manager)
    "historical_frequency",
    "is_duplicate",
    "priority_score",
    "final_priority",
    "recommended_action",
    "escalation_reason",
    "assigned_route"
]

# Keys used only while the program is running.
# visual_evidence_path is an absolute path on the reporter's
# computer, so it is not stored (it breaks on other machines).
TRANSIENT_FIELDS: tuple[str, ...] = (
    "visual_evidence_path",
)


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

        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

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
# BUILD FINAL RECORD
# ============================================================

def build_final_record(
    record: dict[str, Any]
) -> dict[str, Any]:
    """
    Returns a clean copy of an incident ready for storage.

    - Schema fields come first, in RECORD_FIELDS order.
      Missing schema fields are stored as None.
    - Any extra fields are kept after the schema fields.
    - Runtime-only fields are removed.
    - IO_Manager's "image_patch" key is stored as "image_path".

    The original record is not modified.
    """

    clean = dict(record)

    # IO_Manager returns the image under "image_patch"
    image_value = clean.pop("image_patch", "")

    if not clean.get("image_path"):
        clean["image_path"] = image_value or ""

    for key in TRANSIENT_FIELDS:
        clean.pop(key, None)

    final_record = {
        key: clean.get(key)
        for key in RECORD_FIELDS
    }

    for key, value in clean.items():
        if key not in final_record:
            final_record[key] = value

    return final_record


# ============================================================
# GENERATE INCIDENT ID
# ============================================================

def generate_incident_id(
    records: list[dict[str, Any]]
) -> str:
    """
    Generates the next incident ID based on the highest
    existing ID in hazardreportdb.json.
    """

    highest_id = 0

    for record in records:
        incident_id = str(record.get("incident_id", ""))

        if incident_id.startswith("INCIDENT-"):
            number = incident_id[len("INCIDENT-"):]

            if number.isdigit():
                highest_id = max(highest_id, int(number))

    return f"INCIDENT-{highest_id + 1:03d}"


# ============================================================
# SAVE INCIDENT (INPUT + AI ASSESSMENT + DECISION)
# ============================================================

def save(record: dict[str, Any]) -> bool:
    """
    Saves one complete incident into hazardreportdb.json.

    Assigns an incident ID, timestamp and default status
    if they are missing. These are also written back to the
    given record so the caller can display them.
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

    if not record.get("incident_id"):
        record["incident_id"] = generate_incident_id(records)

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

    records.append(build_final_record(record))

    return write_json(get_db_path(), records)


# ============================================================
# QUERY INCIDENTS
# ============================================================

def query(
    filter_fn: Callable[[dict[str, Any]], bool]
) -> list[dict[str, Any]]:
    """
    Filters incidents using a function.

    Example:
        query(lambda r: r.get("status") == "Pending Review")
    """

    if not callable(filter_fn):
        logger.error("query() requires a filter function.")
        return []

    records = load()

    if last_load_warning:
        return []

    return [
        record
        for record in records
        if filter_fn(record)
    ]


def get_incident_by_id(
    incident_id: str
) -> Optional[dict[str, Any]]:
    """
    Returns the incident with the given ID, or None.
    """

    matches = query(
        lambda record: record.get("incident_id") == incident_id
    )

    return matches[0] if matches else None


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
    Deletes an incident (including its AI assessment) by ID.
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
    Clears all incidents (including their AI assessments).
    """

    load()

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

    fieldnames: list[str] = []

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
