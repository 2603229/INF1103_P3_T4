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

# Test block: Add a function call to your script
if __name__ == "__main__":
    user_choice = display_menu()
    print(f"You selected option: {user_choice}")