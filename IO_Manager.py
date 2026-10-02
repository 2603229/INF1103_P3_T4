# Import module statements
import re
from typing import Any, Optional

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
    print("3. Query Incidents by Location or Asset")
    print("4. Export Incidents to Excel Report")
    print("5. Clear All Logged Records")
    print("6. Mark Incident as Resolved")
    print("7. Delete Specific Incident Record")
    print("8. Exit")

    # Enforce strict numeric range validation loop (1 to 8)
    while True:
        choice = input("Select an option (1-8): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= 8:
            return choice
        print("[Error] Invalid input. Please enter a valid number between 1 and 8.")

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

    # Compile validated fields into a structured dictionary record 
    record: dict[str, Any] = {
        "reporter_name": reporter_name
        }
    return record
        
# Test block: Add a function call to your script
if __name__ == "__main__":
    # Test the main menu
    selected_option = display_menu()
    print(f"\nYou selected option: {selected_option}")

    # Test gathering user input if option 1 was selected
    if selected_option == "1":
        user_data = get_user_input()
        print("\nCaptured Record:")
        print(user_data)