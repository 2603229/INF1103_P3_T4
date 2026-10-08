"""
Module Name: data_manager.py
Purpose: Persistence for the system. Stores incident records in a JSON flat
         file, reloads them across runs, filters them, and exports an Excel
         report for facilities management.
 
Never crashes on a missing or corrupt file: problems are logged (logging
module, no print) and an empty list is returned. A corrupt file is renamed
to a .corrupt-<timestamp> backup so a later save cannot destroy it.
"""
 
import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Optional
 
logger = logging.getLogger("hazard.data")
 
# Default: the folder this file lives in (the project root), so the database
# sits next to the code no matter which directory the program is started from.
# Docker overrides this with HAZARD_DATA_DIR=/app/data (a mountable volume).
DEFAULT_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILENAME = "incidents_database.json"
EXPORT_FILENAME = "safety_report.xlsx"
 
Record = dict[str, Any]
 
 
# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
 
def get_data_dir() -> str:
    """Data folder (project root by default); override with HAZARD_DATA_DIR."""
    return os.environ.get("HAZARD_DATA_DIR", DEFAULT_DATA_DIR)
 
 
def get_db_path() -> str:
    """Full path of the JSON database file."""
    return os.path.join(get_data_dir(), DB_FILENAME)
 
 
# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------
 
def load_with_status() -> tuple[list[Record], Optional[str]]:
    """
    Loads all records. Returns (records, warning). `warning` is None when all
    is well, or a message when the file was unreadable/corrupt (records is
    then an empty list). A missing file is normal on first run: no warning.
    """
    path = get_db_path()
    if not os.path.exists(path):
        return [], None
 
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as err:
        backup = f"{path}.corrupt-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        try:
            os.replace(path, backup)
            note = f"backed up to '{backup}'"
        except OSError:
            note = "backup failed"
        logger.error("Database corrupt (%s); %s.", err, note)
        return [], f"Database file was corrupt and has been reset ({note})."
    except OSError as err:
        logger.error("Could not read database: %s", err)
        return [], f"Could not read the database file ({err})."
 
    if not isinstance(data, list):
        logger.error("Database has unexpected structure (%s).", type(data).__name__)
        return [], "Database file had an unexpected structure and was ignored."
 
    return [r for r in data if isinstance(r, dict)], None
 
 
def load() -> list[Record]:
    """Loads all saved records; empty list if missing or corrupt. Never raises."""
    return load_with_status()[0]
 
 
def save_all(records: list[Record]) -> bool:
    """
    Overwrites the database with `records`. Written to a temp file and then
    swapped in, so a crash mid-write cannot leave a half-written database.
    """
    path = get_db_path()
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
 
 
def save(record: Record) -> bool:
    """Appends one processed record to the database."""
    records = load()
    records.append(record)
    return save_all(records)


# ---------------------------------------------------------------------------
# Query  
# ---------------------------------------------------------------------------

def query(filter_fn: Callable[[Record], bool]) -> list[Record]:
    """Returns all stored records for which filter_fn(record) is True."""
    matches: list[Record] = []
    for r in load():
        try:
            if filter_fn(r):
                matches.append(r)
        except Exception as err:  # noqa: BLE001 - a bad filter must not crash the app
            logger.error("Filter function failed on a record: %s", err)
    return matches


def matches_keyword(keyword: str) -> Callable[[Record], bool]:
    """Builds a filter_fn: case-insensitive keyword in location or asset."""
    needle = keyword.strip().lower()

    def _filter(r: Record) -> bool:
        return needle in str(r.get("location", "")).lower() or needle in str(r.get("asset_info", "")).lower()

    return _filter



