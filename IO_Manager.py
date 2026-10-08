# Import module statements
from ast import If
from builtins import dict
import re
import json
import os
import base64
from typing import Any, Optional
from collections import Counter

import shutil
import tkinter as tk
from tkinter import filedialog


# ERROR HANDLING for JSON file path
# Use an absolute path based on the script's location using os.path.dirname(__file__):
## With BASE_DIR: No matter where the terminal is launch from, DB_FILE will always point 
## directly inside the folder where the script lives to ensure that it is accessing the write folder.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "hazardreportdb.json")


# ==============================================================================
# JSON DATABASE HELPER FUNCTIONS
# ==============================================================================
def load_reports() -> list[dict[str, Any]]:
    """Loads reports from the JSON database file.

    Returns an empty list if the file doesn't exist or is empty.
    """
    if not os.path.exists(DB_FILE):
        return []

    try:
        with open(DB_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, FileNotFoundError):
        # File is empty or improperly formatted
        return []
    

def save_reports(reports: list[dict[str, Any]]) -> None:
    """Saves the list of hazard reports to the JSON database file."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as file:
            json.dump(reports, file, indent=4)
        print(f"Data successfully saved to {DB_FILE}")
    except Exception as e:
        print(f"Error saving data to {DB_FILE}: {e}")

# Display main menu
def display_menu() -> str:
    """
    Displays the main interactive CLI menu, strips whitespace, 
    and strictly loops until the user enters a valid option number between 1 and 8.
    """
    print("\n==============================================")
    print("     CAMPUS SAFETY HAZARD REPORTING SYSTEM      ")
    print("==============================================")
    print("1. Submit New Hazard Report")
    print("2. View All Logged Incidents")
    print("3. View Top 5 Most Frequent Hazards")
    print("4. Export Incidents to Excel Report")
    print("5. Exit")

    # Enforce strict numeric range validation loop (1 to 5)
    while True:
        choice = input("Select an option (1-5): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= 8:
            return choice
        print("[Error] Invalid input. Please enter a valid number between 1 and 5.")

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
            print("Error: Please enter a valid name (letters and spaces only, no numbers).")
        else:
            break

    # Step 2: Validate Institutional Contact (SIT email domain or 8-11 digit phone number)
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

    # Step 8: Handle optional image attachment (Base64 encoding for JSON embedding)
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

# OPTIONAL : allows the user to upload an image of the hazard
def select_image_via_dialog() -> str:
    """Opens a native OS file picker window allowing the user to select an image.

    Copies the chosen image to the project's 'uploads/' folder and returns the
    relative path string for JSON storage.
    """
    # Create the uploads folder inside the project directory if it doesn't exist
    upload_dir = os.path.join(BASE_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    print("\nOpening file picker window... Please select an image file.")

    # Initialize tkinter root window and hide the main Tk background window
    ## It uses Python's tkinter.filedialog module to pop up a native OS file selection window (Windows Explorer or macOS Finder) over your terminal.
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # Bring window to front above terminal
            
    # Open OS File Selection Dialog (Filters for common image extensions)
    file_path = filedialog.askopenfilename(
        title="Select Hazard Image",
        filetypes=[
            ("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
            ("All Files", "*.*"),
        ],
    )

    # Destroy tkinter instance after file selection
    root.destroy()

    ## If the user closes/cancels the file picker window without selecting a file, it prints a message and returns an empty string "".
    if not file_path:
        print("ℹNo image selected. Continuing without image.")
        return ""

    # Copy selected file into the local 'uploads/' folder
    filename = os.path.basename(file_path)
    destination = os.path.join(upload_dir, filename)

    try:
        shutil.copy(file_path, destination)
        print(f"Image attached and saved to: uploads/{filename}")
        return f"uploads/{filename}"
    except Exception as e:
        print(f"Error copying image file: {e}")
        return ""
    
def main() -> None:
    """Main execution loop for the Campus Safety Hazard Reporting System."""
    # Load any existing reports from hazardreportdb.json upon startup
    hazard_reports = load_reports()

    while True:
        selected_option = display_menu()

        if selected_option == "1":
            # Collect user input for a new hazard report
            user_data = get_user_input()
            hazard_reports.append(user_data)
            # Persist update directly to hazardreportdb.json
            save_reports(hazard_reports)
            # Print confirmation message after successful submission
            print("\n✅ Hazard report successfully submitted!")

        elif selected_option == "2":
            view_all_reports(hazard_reports)

        elif selected_option == "3":
            view_frequent_hazards(hazard_reports)

        elif selected_option == "5":
            print("\nExiting Campus Safety Hazard Reporting System. Goodbye!")
            break

        else:
            print(
                f"\nInvalid Option: '{selected_option}'. Please select a valid"
                " menu option between 1 and 5."
            )


# Standard Python entry point
## Import Safeguard: Keeping if __name__ == "__main__": main() at the very bottom ensures that if you import this script into another file 
## (such as a testing module or web app), the CLI loop won't automatically execute on import.
if __name__ == "__main__":
    main()
