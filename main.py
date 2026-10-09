
"""
Module Name: main.py

Purpose:
Main application controller for the Campus Safety Hazard Reporting System.

Integration flow:
1. I/O Manager collects and validates user input.
2. AI Manager analyses the hazard report.
3. Logic Manager evaluates risk, priority and duplicates.
4. Data Manager saves and retrieves incident records.
5. I/O Manager displays results to the user.

This application follows procedural programming principles.
"""

import os
import logging
from typing import Any
import subprocess 
import sys 


from dotenv import load_dotenv

# Load API key and other environment variables
load_dotenv()

# ============================================================
# IMPORT TEAMMATES' MODULES
# ============================================================

import IO_Manager
import Data_Manager

from ai_manager import validate_response

from logic_manager import (
    process_record,
    handle_ai_failure,
    calculate_historical_frequency,
    evaluate,
    check_duplicate,
    sort_incidents_by_severity,
)
subprocess.Popen([ 
    sys.executable, "-m", "streamlit", "run", "staff_ui/management_ui.py" 
])


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def prepare_image_path(record: dict[str, Any]) -> None:
    """
    Converts the I/O Manager's image_patch field into the
    visual_evidence_path field expected by the Logic Manager
    and AI Manager.

    The original image_patch field is preserved.
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
                os.path.dirname(os.path.abspath(__file__)),
                image_path
            )

        record["visual_evidence_path"] = image_path

    else:
        record["visual_evidence_path"] = ""


def display_incident_result(record: dict[str, Any]) -> None:
    """
    Displays the final result after successful submission.

    All user-facing output is delegated to the I/O Manager.
    """

    IO_Manager.view_all_reports([record])

    print("\n========== AI RISK ASSESSMENT ==========")

    print(
        "Incident ID:",
        record.get("incident_id", "N/A")
    )

    print(
        "Category:",
        record.get("category", "N/A")
    )

    print(
        "Severity:",
        record.get("severity", "N/A")
    )

    print(
        "Operational Impact:",
        record.get("operational_impact", "N/A")
    )

    print(
        "Risk Summary:",
        record.get("risk_summary", "N/A")
    )

    print(
        "Priority Score:",
        record.get("priority_score", "N/A")
    )

    print(
        "Final Priority:",
        record.get("final_priority", "N/A")
    )

    print(
        "Recommended Action:",
        record.get("recommended_action", "N/A")
    )

    print(
        "Assigned Route:",
        record.get("assigned_route", "N/A")
    )

    print(
        "Duplicate Check:",
        record.get("is_duplicate", "N/A")
    )

    print(
        "Status:",
        record.get("status", "N/A")
    )

    print("========================================")


# ============================================================
# OPTION 1: SUBMIT NEW HAZARD REPORT
# ============================================================

def submit_hazard_report() -> None:
    """
    Coordinates the complete hazard reporting workflow.

    I/O -> AI -> Logic -> Data -> I/O
    """

    print("\n==============================================")
    print("          NEW HAZARD REPORT WORKFLOW          ")
    print("==============================================")

    # --------------------------------------------------------
    # STEP 1: COLLECT USER INPUT
    # --------------------------------------------------------

    try:
        record = IO_Manager.get_user_input()

    except (KeyboardInterrupt, EOFError):
        print("\n[Notice] Report submission cancelled.")
        return

    if not isinstance(record, dict):
        print("[Error] Invalid report data received.")
        return

    # --------------------------------------------------------
    # STEP 2: PREPARE IMAGE EVIDENCE
    # --------------------------------------------------------

    prepare_image_path(record)

    # --------------------------------------------------------
    # STEP 3: LOAD EXISTING INCIDENT RECORDS
    # --------------------------------------------------------

    existing_records = Data_Manager.load()

    if Data_Manager.last_load_warning:
        print(
            "[Warning]",
            Data_Manager.last_load_warning
        )

        # Do not overwrite an unreadable database.
        if os.path.exists(Data_Manager.get_db_path()):
            print(
                "[Error] Submission stopped to protect "
                "the existing database."
            )
            return

    # --------------------------------------------------------
    # STEP 4: SEND REPORT THROUGH AI MANAGER
    # --------------------------------------------------------

    print("\n[Processing] Analysing hazard report...")

    try:
        ai_result = process_record(record)

        if not isinstance(ai_result, dict):
            raise ValueError("Invalid AI result format")

        if not validate_response(ai_result):
            logger.warning(
                "AI result failed validation. "
                "Using offline fallback."
            )
            ai_result = handle_ai_failure(record)

    except Exception as error:

        logger.error(
            "AI processing failed: %s",
            error
        )

        ai_result = handle_ai_failure(record)

    # Merge assessment fields into original report
    record.update(ai_result)

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
    # STEP 7: PRIORITY EVALUATION
    # --------------------------------------------------------

    try:
        decision = evaluate(record)

    except Exception as error:

        logger.error(
            "Logic evaluation failed: %s",
            error
        )

        print(
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
    # STEP 9: DISPLAY ASSESSMENT SUMMARY
    # --------------------------------------------------------

    print("\n========== PRE-SUBMISSION SUMMARY ==========")

    print(
        "Location:",
        record.get("location", "N/A")
    )

    print(
        "Hazard:",
        record.get("asset_info", "N/A")
    )

    print(
        "Severity:",
        record.get("severity", "N/A")
    )

    print(
        "Priority:",
        record.get("final_priority", "N/A")
    )

    print(
        "Recommended Action:",
        record.get("recommended_action", "N/A")
    )

    print(
        "Duplicate Check:",
        record.get("is_duplicate", "N/A")
    )

    print("============================================")

    # --------------------------------------------------------
    # STEP 10: CONFIRM SUBMISSION
    # --------------------------------------------------------

    while True:

        confirmation = input(
            "\nConfirm hazard report submission? (y/n): "
        ).strip().lower()

        if confirmation in ("y", "yes", "n", "no"):
            break

        print(
            "[Error] Please enter y or n."
        )

    if confirmation in ("n", "no"):

        print(
            "\n[Notice] Hazard report submission cancelled."
        )
        return

    # --------------------------------------------------------
    # STEP 11: SAVE THROUGH DATA MANAGER
    # --------------------------------------------------------

    try:
        success = Data_Manager.save(record)

    except Exception as error:

        logger.error(
            "Database save failed: %s",
            error
        )

        success = False

    if not success:

        print(
            "\n[Error] Failed to save hazard report."
        )
        return

    # The Data Manager assigns incident ID and timestamp.
    print(
        "\n[Success] Hazard report saved successfully!"
    )

    # --------------------------------------------------------
    # STEP 12: DISPLAY FINAL RESULT
    # --------------------------------------------------------

    display_incident_result(record)


# ============================================================
# OPTION 2: VIEW ALL INCIDENTS
# ============================================================

def view_all_incidents() -> None:
    """
    Retrieves incidents from the Data Manager,
    sorts them by severity, and displays them.
    """

    records = Data_Manager.load()

    if Data_Manager.last_load_warning:
        print(
            "[Warning]",
            Data_Manager.last_load_warning
        )

    if not records:

        print(
            "\n[Notice] No hazard reports found."
        )
        return

    sorted_records = sort_incidents_by_severity(
        records
    )

    IO_Manager.view_all_reports(
        sorted_records
    )


# ============================================================
# OPTION 3: VIEW TOP 5 FREQUENT HAZARDS
# ============================================================

def view_top_five_hazards() -> None:
    """
    Retrieves stored incident records and displays
    the five most frequently reported hazard types.
    """

    records = Data_Manager.load()

    if Data_Manager.last_load_warning:
        print(
            "[Warning]",
            Data_Manager.last_load_warning
        )

    IO_Manager.view_frequent_hazards(
        records,
        top_n=5
    )


# ============================================================
# MAIN APPLICATION MENU
# ============================================================

def main() -> None:
    """
    Main application loop.

    Coordinates the four menu options provided
    by the team's current IO_Manager.py.
    """

    print("\n==============================================")
    print("   CAMPUS SAFETY HAZARD REPORTING SYSTEM")
    print("==============================================")

    print(
        "System initialized successfully."
    )

    while True:

        try:

            # Display validated menu from I/O Manager
            choice = IO_Manager.display_menu()

            # OPTION 1: SUBMIT REPORT
            if choice == "1":

                submit_hazard_report()

            # OPTION 2: VIEW INCIDENTS
            elif choice == "2":

                view_all_incidents()

            # OPTION 3: TOP FIVE HAZARDS
            elif choice == "3":

                view_top_five_hazards()

            # OPTION 4: EXIT
            elif choice == "4":

                print(
                    "\nExiting Campus Safety Hazard "
                    "Reporting System. Goodbye!"
                )
                break

            else:

                print(
                    "\n[Error] Invalid menu option."
                )

        except KeyboardInterrupt:

            print(
                "\n\n[Notice] Application interrupted by user."
            )
            break

        except EOFError:

            print(
                "\n[Notice] Input stream closed."
            )
            break

        except Exception as error:

            logger.exception(
                "Unexpected application error: %s",
                error
            )

            print(
                "\n[Error] An unexpected error occurred. "
                "Please review the error log."
            )


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
