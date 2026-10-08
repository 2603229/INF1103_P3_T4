"""
Module Name: main.py
Purpose: Serves as the primary entry point and orchestrator for the 
         Campus Safety Hazard Reporting System. Coordinates IO, AI, Logic, and Data.
"""

import sys
from dotenv import load_dotenv
from typing import Any, Callable, cast

# Load environment variables from the local .env file
load_dotenv()

from io_manager import (
    display_menu,
    get_user_input,
    get_confirmation,
    confirm_clear,
    get_search_keyword,
    select_incident_interactively as _select_incident_interactively,  # type: ignore[reportUnknownVariableType]
    display_summary as _display_summary,  # type: ignore[reportUnknownVariableType]
    display_result as _display_result,  # type: ignore[reportUnknownVariableType]
    display_list as _display_list,  # type: ignore[reportUnknownVariableType]
    display_message as _display_message,  # type: ignore[reportUnknownVariableType]
)

# Type-safe casting for IO manager functions
select_incident_interactively: Callable[[list[dict[str, Any]]], str | None] = cast(
    Callable[[list[dict[str, Any]]], str | None],
    _select_incident_interactively,
)
display_summary: Callable[[str | None], None] = cast(
    Callable[[str | None], None],
    _display_summary,
)
display_result: Callable[[dict[str, Any]], None] = cast(
    Callable[[dict[str, Any]], None],
    _display_result,
)
display_list: Callable[[list[dict[str, Any]]], None] = cast(
    Callable[[list[dict[str, Any]]], None],
    _display_list,
)
display_message: Callable[[str], None] = cast(
    Callable[[str], None],
    _display_message,
)

from ai_manager import (
    build_prompt as _build_prompt,  # type: ignore[reportUnknownVariableType]
    call_api as _call_api,  # type: ignore[reportUnknownVariableType]
    parse_response as _parse_response,  # type: ignore[reportUnknownVariableType]
    validate_response as _validate_response,  # type: ignore[reportUnknownVariableType]
)

# Type-safe casting for AI manager functions
build_prompt: Callable[[dict[str, Any]], str] = cast(
    Callable[[dict[str, Any]], str],
    _build_prompt,
)
call_api: Callable[[str, str | None], str] = cast(
    Callable[[str, str | None], str],
    _call_api,
)
parse_response: Callable[[Any], dict[str, Any] | None] = cast(
    Callable[[Any], dict[str, Any] | None],
    _parse_response,
)
validate_response: Callable[[dict[str, Any]], bool] = cast(
    Callable[[dict[str, Any]], bool],
    _validate_response,
)

from logic_manager import (
    score as _score,  # type: ignore[reportUnknownVariableType]
    route as _route,  # type: ignore[reportUnknownVariableType]
    check_duplicate as _check_duplicate,  # type: ignore[reportUnknownVariableType]
    sort_incidents_by_severity as _sort_incidents_by_severity,  # type: ignore[reportUnknownVariableType]
)

# Type-safe casting for Logic manager functions
score: Callable[[dict[str, Any]], float] = cast(
    Callable[[dict[str, Any]], float],
    _score,
)
route: Callable[[dict[str, Any]], str] = cast(
    Callable[[dict[str, Any]], str],
    _route,
)
check_duplicate: Callable[[dict[str, Any], list[dict[str, Any]]], bool] = cast(
    Callable[[dict[str, Any], list[dict[str, Any]]], bool],
    _check_duplicate,
)
sort_incidents_by_severity: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] = cast(
    Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    _sort_incidents_by_severity,
)

from data_manager import (
    load as _load,  # type: ignore[reportUnknownVariableType]
    save as _save,  # type: ignore[reportUnknownVariableType]
    query as _query,  # type: ignore[reportUnknownVariableType]
    clear_database, 
    export_incidents_to_txt, 
    update_incident_status as _update_incident_status,  # type: ignore[reportUnknownVariableType]
    delete_incident_by_id as _delete_incident_by_id,  # type: ignore[reportUnknownVariableType]
)

# Type-safe casting for Data manager functions
load = _load
save: Callable[[list[dict[str, Any]]], bool] = cast(
    Callable[[list[dict[str, Any]]], bool],
    _save,
)
query: Callable[[str], list[dict[str, Any]]] = cast(
    Callable[[str], list[dict[str, Any]]],
    _query,
)
update_incident_status: Callable[[str, str], bool] = cast(
    Callable[[str, str], bool],
    _update_incident_status,
)
delete_incident_by_id: Callable[[str], bool] = cast(
    Callable[[str], bool],
    _delete_incident_by_id,
)

def generate_incident_id(records: list[dict[str, Any]]) -> str:
    """
    Generates a unique incremental incident ID by scanning the highest existing ID number.
    Example: If 'INCIDENT-002' is the highest, returns 'INCIDENT-003'.
    """
    if not records:
        return "INCIDENT-001"
    
    max_num = 0
    for r in records:
        inc_id = r.get("incident_id", "")
        try:
            # Extract numerical sequence after hyphen (e.g., "INCIDENT-002" -> 2)
            num = int(inc_id.split("-")[1])
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            continue
            
    return f"INCIDENT-{max_num + 1:03d}"

def main():
    """Main application loop coordinating user actions and backend processing."""
    while True:
        # Display the main console menu and retrieve validated user choice (1-8)
        choice = display_menu()
        
        if choice == "1":
            # ==========================================
            # 1. Submit New Hazard Report Pipeline
            # ==========================================
            
            # Step A: Capture validated user input fields
            record = get_user_input()
            
            # Step B: Build prompt, query Gemini AI API, and parse response
            prompt = build_prompt(record)
            raw_response = call_api(prompt, record.get("visual_evidence"))
            parsed_data = parse_response(raw_response)
            
            # Step C: Validate AI schema; use intelligent fallback defaults if validation fails
            if parsed_data and validate_response(parsed_data):
                record.update(parsed_data)
            else:
                display_message("[Warning] AI validation failed or fallback triggered. Using default assessment.")
                record.update({
                    "risk_summary": "- Unverified assessment due to network or parsing issue.",
                    "category": "General",
                    "severity": "Medium",
                    "operational_impact": "Moderate",
                    "contextual_insights": "Standard facility review recommended."
                })
            
            # Step D: Calculate mathematical priority score and determine operational route queue
            record["priority_score"] = score(record)
            record["final_priority"] = route(record)
            
            # Step E: Check database for duplicate active reports and set initial review status
            existing_records = load()
            record["is_duplicate"] = check_duplicate(record, existing_records)
            record["status"] = "Pending Review"
            
            # Step F: Display pre-submission AI risk summary for user review
            display_summary(record.get("risk_summary"))
            
            # Step G: Prompt confirmation before persisting to the database
            confirm = get_confirmation()
            if confirm == "y":
                # Assign unique sequential ID and append to records list
                record["incident_id"] = generate_incident_id(existing_records)
                existing_records.append(record)
                
                # Sort records by severity and persist to JSON storage
                sorted_records = sort_incidents_by_severity(existing_records)
                if save(sorted_records):
                    display_result(record)
                else:
                    display_message("[Error] Failed to save record to database.")
            else:
                display_message("[Notice] Report submission cancelled.")
                
        elif choice == "2":
            # ==========================================
            # 2. View All Logged Incidents
            # ==========================================
            records = load()
            sorted_records = sort_incidents_by_severity(records)
            display_list(sorted_records)
            
        elif choice == "3":
            # ==========================================
            # 3. Query Incidents by Location or Asset
            # ==========================================
            keyword = get_search_keyword()
            if keyword:
                results = query(keyword)
                display_list(results)
            else:
                display_message("[Notice] Search keyword cannot be empty.")
                
        elif choice == "4":
            # ==========================================
            # 4. Export Incidents to Excel Report
            # ==========================================
            success = export_incidents_to_txt("safety_report.xlsx")
            if success:
                display_message("\n[Success] All incident records successfully exported to 'safety_report.xlsx'!")
            else:
                display_message("\n[Notice] No records found to export.")
                
        elif choice == "5":
            # ==========================================
            # 5. Clear All Logged Records
            # ==========================================
            confirm = confirm_clear()
            if confirm == "y":
                if clear_database():
                    display_message("\n[Success] All incident records have been permanently cleared.")
                else:
                    display_message("[Error] Failed to clear database.")
            else:
                display_message("[Notice] Clear action cancelled.")
                
        elif choice == "6":
            # ==========================================
            # 6. Mark Incident as Resolved
            # ==========================================
            records = load()
            if not records:
                display_message("\n[Notice] No incident records found in the database.")
            else:
                inc_id = select_incident_interactively(records)
                if inc_id:
                    success = update_incident_status(inc_id, "Resolved")
                    if success:
                        display_message(f"\n[Success] Incident {inc_id} has been marked as Resolved!")
                    else:
                        display_message(f"\n[Error] Incident ID '{inc_id}' not found.")
                else:
                    display_message("\n[Notice] Operation cancelled.")
                
        elif choice == "7":
            # ==========================================
            # 7. Delete Specific Incident Record
            # ==========================================
            records = load()
            if not records:
                display_message("\n[Notice] No incident records found in the database.")
            else:
                inc_id = select_incident_interactively(records)
                if inc_id:
                    success = delete_incident_by_id(inc_id)
                    if success:
                        display_message(f"\n[Success] Incident {inc_id} has been permanently deleted from the database.")
                    else:
                        display_message(f"\n[Error] Incident ID '{inc_id}' not found.")
                else:
                    display_message("\n[Notice] Operation cancelled.")

        elif choice == "8":
            # ==========================================
            # 8. Exit Application
            # ==========================================
            display_message("\nExiting Campus Safety System. Stay safe!")
            sys.exit(0)
            
        else:
            display_message("\n[Error] Invalid option selected. Please choose a number between 1 and 8.")

if __name__ == "__main__":
    main()