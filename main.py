"""
INF1103 Team 4
Campus Safety Hazard Reporting System

MAIN APPLICATION INTEGRATION

Workflow:
1. IO_Manager collects user input.
2. ai_manager analyses the hazard report.
3. logic_manager calculates priority and routing.
4. Data_Manager saves ONE complete record (input + AI assessment
   + decision) into hazardreportdb.json.

All JSON file operations are handled by Data_Manager.py.
"""

import os
import logging
import subprocess 
import sys 
from typing import Any, cast

from dotenv import load_dotenv

import IO_Manager
import Data_Manager

from ai_manager import validate_response

from logic_manager import (
    process_record,
    handle_ai_failure,
    calculate_historical_frequency,
    evaluate,
    check_duplicate,
    sort_incidents_by_severity
)


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# The only fields taken from the AI result. Copying just these
# stops an unexpected AI key from overwriting reporter data
# such as "location" or "incident_id".
AI_FIELDS: tuple[str, ...] = (
    "risk_summary",
    "category",
    "severity",
    "operational_impact",
    "contextual_insights"
)

OFFLINE_MARKER = "[Offline Assessment]"


# ============================================================
# IMAGE PATH INTEGRATION
# ============================================================

def prepare_image_path(record: dict[str, Any]) -> None:
    """
    Converts the relative image path from IO_Manager into
    an absolute path usable by AI Manager.

    The absolute path is only used while the program runs;
    Data_Manager stores the relative path instead.
    """

    image_path = (
        record.get("image_patch")
        or record.get("visual_evidence_path")
        or ""
    )

    if image_path:
        image_path = str(image_path).strip()

        if not os.path.isabs(image_path):
            image_path = os.path.join(
                BASE_DIR,
                image_path
            )

        record["visual_evidence_path"] = image_path

    else:
        record["visual_evidence_path"] = ""


# ============================================================
# AI ASSESSMENT
# ============================================================

def run_ai_assessment(
    record: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    """
    Sends the record through the AI layer and returns
    (assessment, assessment_source).

    process_record() already returns the offline fallback
    when Gemini is unavailable, so that case is detected
    first instead of being validated (the fallback uses
    categories outside the Gemini schema and would fail
    validation, causing a second, misleading fallback).
    """

    try:
        ai_result: Any = process_record(record)

    except Exception as error:

        logger.error(
            "AI processing failed: %s",
            error
        )

        return handle_ai_failure(record), "Offline Fallback"

    if not isinstance(ai_result, dict):

        logger.warning(
            "AI returned a non-dictionary result. "
            "Applying offline fallback."
        )

        return handle_ai_failure(record), "Offline Fallback"

    ai_result = cast(dict[str, Any], ai_result)
    risk_summary = str(ai_result.get("risk_summary", ""))

    if OFFLINE_MARKER in risk_summary:
        return ai_result, "Offline Fallback"

    if not validate_response(ai_result):

        logger.warning(
            "Gemini result failed schema validation. "
            "Applying offline fallback."
        )

        return handle_ai_failure(record), "Offline Fallback"

    return ai_result, "Gemini AI"

# ============================================================
# OPTION 1: SUBMIT NEW HAZARD REPORT
# ============================================================

def submit_hazard_report() -> None:
    """
    Complete integration workflow:

    IO -> AI -> Logic -> Data
    """

    IO_Manager.display_workflow_header()

    # --------------------------------------------------------
    # STEP 1: COLLECT USER INPUT
    # --------------------------------------------------------

    try:
        record = IO_Manager.get_user_input()

    except (KeyboardInterrupt, EOFError):
        IO_Manager.display_message(
            "\n[Notice] Report submission cancelled."
        )
        return

    if not record:
        IO_Manager.display_message(
            "[Error] Invalid report information."
        )
        return

    # --------------------------------------------------------
    # STEP 2: PREPARE IMAGE PATH
    # --------------------------------------------------------

    prepare_image_path(record)

    # --------------------------------------------------------
    # STEP 3: LOAD EXISTING INCIDENTS
    # --------------------------------------------------------

    existing_records = Data_Manager.load()

    if Data_Manager.last_load_warning:

        IO_Manager.display_message(
            f"[Warning] {Data_Manager.last_load_warning}"
)

        IO_Manager.display_message(
            "[Error] Submission stopped to protect "
            "the existing database."
        )

        return

    # --------------------------------------------------------
    # STEP 4: AI ASSESSMENT
    # --------------------------------------------------------

    IO_Manager.display_message(
    "\n[Processing] Analysing hazard report..."
)

    ai_result, assessment_source = run_ai_assessment(record)

    # Add only the expected assessment fields to the record
    for key in AI_FIELDS:
        record[key] = ai_result.get(key)

    record["assessment_source"] = assessment_source

    # --------------------------------------------------------
    # STEP 5: HISTORICAL FREQUENCY
    # --------------------------------------------------------

    record["historical_frequency"] = (
        calculate_historical_frequency(
            record,
            existing_records
        )
    )

    # --------------------------------------------------------
    # STEP 6: DUPLICATE DETECTION
    # --------------------------------------------------------

    record["is_duplicate"] = check_duplicate(
        record,
        existing_records
    )

    # --------------------------------------------------------
    # STEP 7: PRIORITY AND ROUTING
    # --------------------------------------------------------

    try:
        decision = evaluate(record)

    except Exception as error:

        logger.error(
            "Logic evaluation failed: %s",
            error
        )

        IO_Manager.display_message(
            "[Error] Unable to evaluate hazard priority."
        )

        return

    record["priority_score"] = decision["score"]

    record["final_priority"] = decision["priority"]

    record["recommended_action"] = decision["action"]

    record["escalation_reason"] = decision["reason"]

    record["assigned_route"] = decision["route"]

    # --------------------------------------------------------
    # STEP 8: INITIAL STATUS
    # --------------------------------------------------------

    record["status"] = "Pending Review"

    # --------------------------------------------------------
    # SHOW RULE-BASED PRIORITY SCORE BEFORE THE SUMMARY
    # --------------------------------------------------------
    IO_Manager.display_priority_calculation(record, decision)

    # --------------------------------------------------------
    # STEP 9: PRE-SUBMISSION SUMMARY
    # --------------------------------------------------------

    IO_Manager.display_pre_submission_summary(record)

    # --------------------------------------------------------
    # STEP 10: CONFIRM SUBMISSION
    # --------------------------------------------------------

    if not IO_Manager.confirm_submission():
        return

    # --------------------------------------------------------
    # STEP 11: SAVE COMPLETE RECORD THROUGH DATA MANAGER
    # --------------------------------------------------------

    # One record = reporter input + AI assessment + decision.
    # main.py does not create or write JSON files.

    try:
        success = Data_Manager.save(record)

    except Exception as error:
        logger.error(
            "Incident database save failed: %s",
            error
        )
        success = False

    if not success:
        IO_Manager.display_message(
            "\n[Error] Failed to save hazard report."
        )
        return

    IO_Manager.display_submission_success(record)


    # --------------------------------------------------------
    # STEP 12: DISPLAY FINAL RESULT
    # --------------------------------------------------------

    IO_Manager.display_incident_result(record)

# ============================================================
# OPTION 2: VIEW ALL INCIDENTS
# ============================================================

def view_all_incidents() -> None:
    """
    Retrieves and displays all incident reports.
    """

    records = Data_Manager.load()

    if Data_Manager.last_load_warning:
        IO_Manager.display_message(
            f"[Warning] {Data_Manager.last_load_warning}"
        )
        return

    if not records:
        IO_Manager.display_message(
            "\n[Notice] No hazard reports found."
        )
        return

    sorted_records = sort_incidents_by_severity(records)

    IO_Manager.view_all_reports(sorted_records)


# ============================================================
# OPTION 3: VIEW TOP FIVE HAZARDS
# ============================================================

def view_top_five_hazards() -> None:
    """
    Displays the five most frequently reported hazards.
    """

    records = Data_Manager.load()

    if Data_Manager.last_load_warning:
        IO_Manager.display_message(
            f"[Warning] {Data_Manager.last_load_warning}"
        )
        return

    IO_Manager.view_frequent_hazards(
        records,
        top_n=5
    )


# ============================================================
# MAIN APPLICATION
# ============================================================


def main() -> None:
    """
    Main application controller.
    """

    streamlit_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run",
         os.path.join(BASE_DIR, "management_ui.py")],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    IO_Manager.display_message(
        "System initialized successfully."
)

    try:
        while True:
            try:
                choice = IO_Manager.display_menu()

                # OPTION 1: SUBMIT REPORT
                if choice == "1":
                    submit_hazard_report()

                # OPTION 2: VIEW ALL REPORTS
                elif choice == "2":
                    view_all_incidents()

                # OPTION 3: VIEW TOP FIVE HAZARDS
                elif choice == "3":
                    view_top_five_hazards()

                # OPTION 4: EXIT
                elif choice == "4":
                    IO_Manager.display_message(
                        "\nExiting Campus Safety Hazard "
                        "Reporting System. Goodbye!"
                    )
                    break

                else:
                    IO_Manager.display_message("\n[Error] Invalid menu option.")

            except KeyboardInterrupt:
                IO_Manager.display_message("\n[Notice] Application interrupted.")
                break

            except EOFError:
                IO_Manager.display_message("\n[Notice] Input stream closed.")
                break

            except Exception as error:
                logger.exception(
                    "Unexpected application error: %s",
                    error
                )

                IO_Manager.display_message("\n[Error] An unexpected error occurred.")

    finally:
        # Stop Streamlit when the CLI application exits
        if streamlit_proc.poll() is None:
            streamlit_proc.terminate()

            try:
                streamlit_proc.wait(timeout=5)

            except subprocess.TimeoutExpired:
                streamlit_proc.kill()
                streamlit_proc.wait()

        IO_Manager.display_message(
    "[Info] Application shutdown completed."
)


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()