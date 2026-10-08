"""
Module Name: data_manager.py
Purpose: Persistence layer. Stores incident records in a JSON flat file
         (incidents_database.json), reloads them across runs, filters them,
         updates / deletes them and exports a CSV report.
 
One function per job: load() reads, save() writes, query() filters.
 
How it fits the other modules:
  - logic_manager.check_duplicate() takes the list that load() returns.
  - management_ui.py reads the same file. By default both use the project
    folder; set INCIDENTS_DB to point both of them at another file.
  - Every stored record is guaranteed an incident_id, a status and a
    timestamp, which management_ui.py and logic_manager rely on.
 
No console output (problems go to the logging module) and no classes.
"""
 
import csv
import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Optional
 
logger = logging.getLogger(__name__)
 
DB_FILENAME = "incidents_database.json"
EXPORT_FILENAME = "safety_report.csv"
DEFAULT_STATUS = "Pending Review"
 
# Default folder: where this file lives (the project root), so the database sits
# next to the code however the program is started.
_THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
 
# Set by every call to load(): a message for the user if the database file was
# unreadable or corrupt, otherwise None. The caller (main) shows it at startup.
last_load_warning: Optional[str] = None
 
 
# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
 
def get_db_path() -> str:
    """
    Full path of the JSON database file. In order of priority:
      1. INCIDENTS_DB      full path to the file (management_ui.py reads this too)
      2. HAZARD_DATA_DIR   folder to keep the file in (Docker uses /app/data)
      3. the project folder
    """
    explicit = os.environ.get("INCIDENTS_DB", "").strip()
    if explicit:
        return explicit
    folder = os.environ.get("HAZARD_DATA_DIR", "").strip() or _THIS_FOLDER
    return os.path.join(folder, DB_FILENAME)
 
 
def get_data_dir() -> str:
    """Folder holding the database; the CSV export and the log go here too."""
    return os.path.dirname(os.path.abspath(get_db_path()))
 
 
# ---------------------------------------------------------------------------
# Load / save / query
# ---------------------------------------------------------------------------
 
def load() -> list[dict[str, Any]]:
    """
    Loads all saved records. Never raises.
 
    - Missing file (normal on first run): returns [].
    - Corrupt or wrong-shaped file: renamed to a .corrupt-<timestamp> backup,
      returns [], and sets last_load_warning.
    - Unreadable file (permissions, I/O error): returns [], sets
      last_load_warning, and leaves the file alone.
    """
    global last_load_warning
    last_load_warning = None
    path = get_db_path()
    if not os.path.exists(path):
        return []
 
    problem = ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        problem = f"unexpected structure ({type(data).__name__}, expected a list)"
    except json.JSONDecodeError as err:
        problem = f"invalid JSON ({err})"
    except OSError as err:
        logger.error("Could not read database: %s", err)
        last_load_warning = f"Could not read the database file ({err})."
        return []
 
    backup = f"{path}.corrupt-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    try:
        os.replace(path, backup)
        note = f"backed up to '{backup}'"
    except OSError:
        note = "backup failed"
    logger.error("Database unusable: %s; %s.", problem, note)
    last_load_warning = f"Database file was corrupt and has been reset ({note})."
    return []
 
 
def save(data: dict[str, Any] | list[dict[str, Any]]) -> bool:
    """
    Writes to the database. Returns True on success, False on failure (logged).
 
    - A single record (dict): appended. The dict you pass is completed in
      place with an incident_id (next INCIDENT-NNN), a status and a timestamp
      if it has none, so read them from it afterwards. A record whose
      incident_id already exists is refused.
    - A list of records: replaces the whole database (used by update/delete).
 
    The file is written to a temp file and then swapped in, so a crash
    mid-write cannot leave a half-written database.
    """
    path = get_db_path()
    if isinstance(data, dict):
        records = load()
        if last_load_warning is not None and os.path.exists(path):
            logger.error("Not saving: the existing database could not be read, and writing would lose it.")
            return False
 
        if not data.get("incident_id"):
            highest = 0
            for r in records:
                digits = str(r.get("incident_id", "")).rsplit("-", 1)[-1]
                if digits.isdigit():
                    highest = max(highest, int(digits))
            data["incident_id"] = f"INCIDENT-{highest + 1:03d}"
        elif any(r.get("incident_id") == data["incident_id"] for r in records):
            logger.error("Not saving: %s already exists.", data["incident_id"])
            return False
        if not data.get("status"):
            data["status"] = DEFAULT_STATUS
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        records.append(data)
    elif isinstance(data, list):
        records = data
    else:
        logger.error("save() needs a record (dict) or a list of records, not %s.", type(data).__name__)
        return False
 
    tmp_path = path + ".tmp"
    try:
        os.makedirs(get_data_dir(), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=4)
        os.replace(tmp_path, path)
        return True
    except PermissionError:
        logger.error("Permission denied writing '%s'.", path)
    except (OSError, TypeError, ValueError) as err:
        logger.error("Could not save database: %s", err)
    return False
 
 
def query(filter_fn: Callable[[dict[str, Any]], bool]) -> list[dict[str, Any]]:
    """
    Returns all stored records for which filter_fn(record) is True, e.g.
        query(lambda r: r.get("severity") == "Critical")
    A filter that raises on a record is logged and skipped, never fatal.
    """
    matches: list[dict[str, Any]] = []
    for r in load():
        try:
            if filter_fn(r):
                matches.append(r)
        except Exception as err:  # noqa: BLE001 - a bad filter must not crash the app
            logger.error("Filter function failed on a record: %s", err)
    return matches
 
 
# ---------------------------------------------------------------------------
# Update / delete / clear
# ---------------------------------------------------------------------------
 
def update_incident_status(incident_id: str, new_status: str = "Resolved") -> bool:
    """Sets the status of one incident (e.g. 'Pending Review' -> 'Resolved')."""
    records = load()
    for r in records:
        if r.get("incident_id") is not None and str(r["incident_id"]) == incident_id:
            r["status"] = new_status
            return save(records)
    return False
 
 
def delete_incident_by_id(incident_id: str) -> bool:
    """Deletes one incident by ID (case-insensitive). False if not found or save failed."""
    records = load()
    target = incident_id.strip().upper()
    remaining = [r for r in records if str(r.get("incident_id", "")).strip().upper() != target]
    if len(remaining) == len(records):
        return False
    return save(remaining)


def clear_database() -> bool:
    """Permanently deletes the database file."""
    try:
        if os.path.exists(get_db_path()):
            os.remove(get_db_path())
        return True
    except OSError as err:
        logger.error("Could not clear database: %s", err)
        return False