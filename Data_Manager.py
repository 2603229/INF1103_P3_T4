"""
Module Name: data_manager.py
Purpose: Manages persistent storage of incident reports in a local JSON database
         and provides facilities management Excel spreadsheet export utilities and status updates with strict type annotations.
"""

import json
import os
from typing import Any, cast
import openpyxl  # <-- Required for Excel file generation

DB_FILENAME = "incidents_database.json"

def load() -> list[dict[str, Any]]:
    """
    Loads all saved incident records from disk storage. 
    Returns an empty list if the database file does not exist or cannot be parsed.
    """
    if not os.path.exists(DB_FILENAME):
        return []
        
    try:
        with open(DB_FILENAME, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure loaded data structure matches a list of dictionaries
            if isinstance(data, list):
                return cast(list[dict[str, Any]], data)
            return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"[Data Error] Could not read database: {e}")
        return []