# Import module statements
import re
import os
import shutil
import uuid

from typing import Any
from collections import Counter

try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    tk = None
    filedialog = None


# ERROR HANDLING for JSON file path
# Use an absolute path based on the script's location using os.path.dirname(__file__):
## With BASE_DIR: No matter where the terminal is launch from, DB_FILE will always point 
## directly inside the folder where the script lives to ensure that it is accessing the write folder.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Display main menu
def display_menu() -> str:
    """
    Displays the main interactive CLI menu, strips whitespace, 
    and strictly loops until the user enters a valid option number between 1 and 4.
    """
    print("\n==============================================")
    print("     CAMPUS SAFETY HAZARD REPORTING SYSTEM      ")
    print("==============================================")
    print("1. Submit New Hazard Report")
    print("2. View All Logged Incidents")
    print("3. View Top 5 Most Frequent Hazards")
    print("4. Exit")

    # Enforce strict numeric range validation loop (1 to 4)
    while True:
        choice = input("Select an option (1-4): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= 4:
            return choice
        print("[Error] Invalid input. Please enter a valid number between 1 and 4.")

# ==============================================================================
# OPTION 1: USER INPUT & SUBMISSION
# ==============================================================================

# It specifies that the function returns a dictionary (dict) with specific types for its keys and values:
#   str (Key Type): All keys in the dictionary must be strings.
#   Any (Value Type): The values inside the dictionary can be of any data type (e.g., strings, numbers, booleans, lists).
def get_user_input() -> dict[str, Any]:

    # Print Header for New Hazard Report Submission
    print("\n--- Submit New Hazard Report (SIT Punggol Coast) ---")
    
    # Step 1: Validate Reporter Name (letters, spaces, apostrophes, periods, and hyphens only)

    # ==============================================================================
    # VALIDATION BREAKDOWN: name_pattern = r"^[A-Za-z\s'\.-]+$"
    # ==============================================================================
    #
    #  r"..."  : Raw string flag. Prevents Python from processing backslashes so
    #            regex escape sequences like '\s' are passed directly to the engine.
    #
    #  ^       : Start Anchor. Forces the match to begin at the very start of the string.
    #
    #  [ ... ] : Character Class. Matches any SINGLE character contained inside the set:
    #            • A-Za-z : Uppercase (A-Z) and lowercase (a-z) letters.
    #            • \s     : Whitespace characters (spaces/tabs) for multi-word names.
    #            • '      : Literal apostrophe for names like O'Connor or D'Silva.
    #            • \.     : Escaped period for initials/titles like St. John or A. Smith.
    #            • -      : Literal hyphen for hyphenated names like Smith-Jones.
    #
    #  +       : Quantifier ("One or more"). Requires at least 1 valid character,
    #            preventing empty inputs from matching.
    #
    #  $       : End Anchor. Forces the match to extend all the way to the end of the string.
    #
    #  ** Combining '^' and '$' ensures the ENTIRE input must strictly consist of
    #     only the allowed characters—rejecting any inputs with numbers or symbols.
    # ==============================================================================
    reporter_name = ""
    name_pattern = r"^[A-Za-z\s'\.-]+$"
    while True:
        reporter_name = input("Enter reporter name (Student/Teacher): ").strip()
        if not reporter_name:
            print("Error: Reporter name cannot be empty.")
        elif not re.match(name_pattern, reporter_name):
            print("Error: Please enter a valid name "
                  "(letters, spaces, apostrophes, periods, and hyphens only)."
)
        else:
            break

    # Step 2: Validate Institutional Contact (SIT email domain or valid 8-digit phone number)
    reporter_contact = ""

    ## Restricts the username strictly to letters and numbers (such as john123@sit.singaporetech.edu.sg)
    email_pattern = r"^[A-Za-z0-9]+@sit\.singaporetech\.edu\.sg$"
    # ==============================================================================
    # ERROR HANDLING FOR PHONE NUMBER VALIDATION
    #  ^        : Start Anchor. Forces the match to begin at the very start of the input.
    #
    #  [689]    : Prefix Character Class. Enforces that the VERY FIRST digit MUST be
    #             either 6 (landline), 8 (mobile/VOIP), or 9 (mobile).
    #
    #  \d{7}    : Digit Quantifier. Requires EXACTLY 7 additional numeric digits (0-9)
    #             immediately following the starting digit.
    #
    #  $        : End Anchor. Forces the match to extend to the end of the string.
    #
    #  SUMMARY  : 1 initial digit + 7 remaining digits = EXACTLY 8 digits total.
    #             Blocks non-numeric characters, wrong starting digits (e.g., starting
    #             with 1, 2, 3, 4, 5, 7), and numbers shorter or longer than 8 digits.
    phone_pattern = r"^[689]\d{7}$"

    while True:
        reporter_contact = input("Enter SIT email (@sit.singaporetech.edu.sg) or phone number: ").strip()
        # john123@sit.singaporetech.edu.sg (All lowercase)
        # John123@SIT.SINGAPORETECH.EDU.SG (All uppercase)
        #JOHN123@sit.SingaporeTech.edu.sg (Mixed case)
        # all three will be recognized as valid without requiring the user to type strictly in lowercase.
        if re.match(email_pattern, reporter_contact, re.IGNORECASE) or re.match(phone_pattern, reporter_contact):
            break
        print("Error: Enter a valid SIT email or a valid 8-digit phone number.")

    # Step 3: Validate Location (non-empty string)
    location = ""
    while not location.strip():
        location = input("Enter location (e.g., SIT@Punggol Coast, Level 3 MakerSpace): ").strip()
        if not location:
            print("Error: Location cannot be empty.")

    #  PURPOSE:
    #  Measures the potential reach/severity of a campus safety hazard by capturing 
    #  the estimated number of people affected (e.g., aircon breakdown in a lecture 
    #  hall affecting ~200 students vs. a broken desk socket affecting 1-2 people).
    impact = 0
    while True:
        impact_input = input("Please enter an estimated number of people that will be affected: ").strip()
        if impact_input.isdigit():
            impact = int(impact_input)
            if 1 <= impact <= 1000:
                break
            print("Error: Please enter a realistic headcount between 1 and 1000.")
        else:
            print("Error: Please enter a valid non-negative number.")

    # Step 6: Validate Asset Info / Brief Hazard Summary (minimum 3 characters required)
    asset_info = ""
    while True:
        asset_info = input("Enter asset or brief hazard summary (e.g., Aircon spoil, Window broken, Wet floor): ").strip()
        if len(asset_info) >= 3:
            break
        print("Error: Please provide at least 3 characters (e.g., 'Wet floor').")
            
    # Step 7: Validate Detailed Description & Risk (minimum 15 characters required for contextual AI analysis)
    description = ""
    while True:
        description = input("Enter elaboration on the risk/safety hazard (e.g., Water pooling near electrical outlet, high slip risk): ").strip()
        if len(description) >= 15:
            break
        print("Error: Description is too brief. Please provide at least 15 characters elaborating on the hazard/risk.")

    # Step 8: Handle optional image attachment
    # Copy the selected image to the uploads/ directory.
    # Store its relative file path instead of embedding Base64 data in JSON.
    print("\nWould you like to attach an image of the hazard?")
    attach_choice = input("Attach image? (y/n): ").strip().lower()

    image_path = ""
    if attach_choice in ["y", "yes"]:
        image_path = select_image_via_dialog()


    # Compile validated fields into a structured dictionary record 
    return {
        "reporter_name": reporter_name,
        "reporter_contact": reporter_contact,
        "location": location,
        "impact_headcount": impact,
        "asset_info": asset_info,
        "description": description,
        "image_patch": image_path  
    }

# To view all submitted hazard reports
def view_all_reports(reports: list[dict[str, Any]]) -> None:
    ## Displays all submitted hazard reports in a structured summary format.
    print("\n==============================================")
    print("           VIEW ALL HAZARD REPORTS            ")
    print("==============================================")

    # Check if there are any reports stored
    if not reports:
        print("No hazard reports submitted yet.")
        print("==============================================")
        return

    print(f"Total Reports Found: {len(reports)}\n")

    # Iterate and display each report with a clear card boundary
    for idx, report in enumerate(reports, start=1):
        print(f"--- Report #{idx} ---")
        print(f"Reporter Name    : {report.get('reporter_name')}")
        print(f"Contact Info     : {report.get('reporter_contact')}")
        print(f"Location         : {report.get('location')}")
        print(f"Affected People  : {report.get('impact_headcount')}")
        print(f"Asset / Summary  : {report.get('asset_info')}")
        print(f"Description      : {report.get('description')}")
        print("-" * 30)

    print("==============================================")


# View Top 5 most frequent hazards
def view_frequent_hazards(
    reports: list[dict[str, Any]], top_n: int = 5
) -> None:
    # Groups reports by asset/hazard summary and displays the top N most frequent hazards.

    # Format in clean header for the top hazards summary
    print("\n==============================================")
    print(f"       TOP {top_n} MOST FREQUENT HAZARD REPORTS       ")
    print("==============================================")

    if not reports:
        print("No hazard reports submitted yet.")
        print("==============================================")
        return

    # Extract all asset_info strings (converted to lowercase for uniform grouping)
    hazard_counts = Counter(
        report.get("asset_info", "Unknown").strip().title()
        for report in reports
    )

    # Get the top N most common hazards
    top_hazards = hazard_counts.most_common(top_n)

    print(
        f"{'Rank':<6} | {'Hazard / Asset Summary':<28} | {'Frequency':<10}"
    )
    print("-" * 50)

    for rank, (hazard, count) in enumerate(top_hazards, start=1):
        print(f"{rank:<6} | {hazard:<28} | {count:<10}")

def select_image_via_dialog() -> str:
    """
    Allows users to attach an optional hazard image.

    Uses a graphical file picker when available.
    Falls back to terminal path input in headless environments.
    Validates supported formats and copies the selected image
    into the project's uploads directory.
    """

    file_path = ""
    use_terminal_input = tk is None or filedialog is None

    # Step 1: Open graphical image picker if available
    if not use_terminal_input:
        root = None

        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)

            file_path = filedialog.askopenfilename(
                title="Select Hazard Image",
                filetypes=[
                    ("Supported Images", "*.png *.jpg *.jpeg *.webp")
                ]
            )

        except (tk.TclError, OSError):
            print(
                "[Info] Graphical file picker unavailable. "
                "Switching to terminal input."
            )
            use_terminal_input = True

        finally:
            if root is not None:
                try:
                    root.destroy()
                except (tk.TclError, OSError):
                    pass

    # Step 2: Allow terminal input if GUI is unavailable
    if use_terminal_input:
        file_path = input(
            "Enter image file path (or press Enter to skip): "
        ).strip().strip('"')

    # Step 3: Handle cancelled or skipped selection
    if not file_path:
        print("[Info] No image selected. Continuing without image.")
        return ""

    # Step 4: Validate file existence
    if not os.path.isfile(file_path):
        print("[Error] Selected image file does not exist.")
        return ""

    # Step 5: Validate supported image formats
    allowed_extensions = (".png", ".jpg", ".jpeg", ".webp")

    if os.path.splitext(file_path)[1].lower() not in allowed_extensions:
        print(
            "[Error] Unsupported image format. "
            "Please select PNG, JPG, JPEG, or WebP."
        )
        return ""

    # Step 6: Copy image to uploads directory
    upload_dir = os.path.join(BASE_DIR, "uploads")

    try:
        os.makedirs(upload_dir, exist_ok=True)

        # Unique filename prevents overwriting existing images
        filename = f"{uuid.uuid4().hex}_{os.path.basename(file_path)}"

        destination = os.path.join(upload_dir, filename)

        shutil.copy2(file_path, destination)

        relative_path = f"uploads/{filename}"

        print(f"[Success] Image attached: {relative_path}")

        return relative_path

    except (OSError, shutil.Error) as error:
        print(f"[Error] Unable to attach image: {error}")
        return ""


def display_priority_calculation(
    record: dict[str, Any], decision: dict[str, Any]
) -> None:
    """Display the rule-based priority score before submission confirmation."""
    breakdown = decision["score_breakdown"]
    severity_score = breakdown["severity"]
    operational_score = breakdown["operational_impact"]
    frequency_score = breakdown["historical_frequency"]

    print("\n========== PRIORITY SCORE CALCULATION ==========")
    print(f"Severity: {record.get('severity', 'Low')} -> +{severity_score}")
    print(
        f"Operational Impact: {record.get('operational_impact', 'Minor')} "
        f"-> +{operational_score}"
    )
    print(
        f"Historical Frequency: {record.get('historical_frequency', 0)} "
        f"-> +{frequency_score}"
    )
    print("-----------------------------------------------")
    print(
        f"Priority Score = {severity_score} + {operational_score} "
        f"+ {frequency_score} = {decision['score']}"
    )
    print(f"Final Priority: {decision['priority']}")
    print("===============================================")


# ============================================================
# TERMINAL DISPLAY AND SUBMISSION FUNCTIONS
# ============================================================

def display_message(message: str) -> None:
    """Displays an application message in the terminal."""
    print(message)


def display_workflow_header() -> None:
    """Displays the new hazard report workflow header."""
    print("\n==============================================")
    print("          NEW HAZARD REPORT WORKFLOW")
    print("==============================================")


def display_pre_submission_summary(
    record: dict[str, Any]
) -> None:
    """Displays hazard details before submission confirmation."""

    print("\n========== PRE-SUBMISSION SUMMARY ==========")
    print("Location:", record.get("location", "N/A"))
    print("Hazard:", record.get("asset_info", "N/A"))
    print("Category:", record.get("category", "N/A"))
    print("Severity:", record.get("severity", "N/A"))
    print("Operational Impact:", record.get("operational_impact", "N/A"))
    print("AI Assessment Source:", record.get("assessment_source", "N/A"))
    print("Priority:", record.get("final_priority", "N/A"))
    print("Recommended Action:", record.get("recommended_action", "N/A"))
    print("Duplicate Check:", record.get("is_duplicate", "N/A"))
    print("============================================")


def confirm_submission() -> bool:
    """Asks the user to confirm or cancel the hazard submission."""

    while True:
        try:
            confirmation = input(
                "\nConfirm hazard report submission? (y/n): "
            ).strip().lower()

        except (KeyboardInterrupt, EOFError):
            print("\n[Notice] Submission cancelled.")
            return False

        if confirmation in ("y", "yes"):
            return True

        if confirmation in ("n", "no"):
            print("\n[Notice] Submission cancelled.")
            return False

        print("[Error] Please enter y or n.")


def display_submission_success(
    record: dict[str, Any]
) -> None:
    """Displays confirmation after the incident is saved."""

    print(
        "\n[Success] Hazard report and AI assessment "
        "saved to hazardreportdb.json!"
    )

    print("Incident ID:", record.get("incident_id", "N/A"))


def display_incident_result(
    record: dict[str, Any]
) -> None:
    """Displays the completed incident and its assessment."""

    view_all_reports([record])

    print("\n========== AI RISK ASSESSMENT ==========")

    fields = (
        ("Incident ID", "incident_id"),
        ("Category", "category"),
        ("Severity", "severity"),
        ("Operational Impact", "operational_impact"),
        ("Risk Summary", "risk_summary"),
        ("Contextual Insights", "contextual_insights"),
        ("Assessment Source", "assessment_source"),
        ("Historical Frequency", "historical_frequency"),
        ("Priority Score", "priority_score"),
        ("Final Priority", "final_priority"),
        ("Recommended Action", "recommended_action"),
        ("Escalation Reason", "escalation_reason"),
        ("Assigned Route", "assigned_route"),
        ("Duplicate Check", "is_duplicate"),
        ("Status", "status"),
    )

    for label, key in fields:
        print(f"{label}: {record.get(key, 'N/A')}")

    print("========================================")