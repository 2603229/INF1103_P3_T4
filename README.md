Campus Safety Hazard Reporting System
A modular, production-grade Python console application designed for front-line campus safety reporting, automated AI risk assessment, intelligent triage routing, persistent JSON data management, and robust input validation at SIT Punggol Coast.
🚀 System Architecture & Modules
The application follows a strict modular architecture to separate concerns, maintain clean interfaces, and enforce hard constraints:
main.py: The primary application orchestrator and entry point. Manages the main interactive menu loop, coordinate workflow sequences, sequential ID generation (INCIDENT-001), and database saves.
io_manager.py: Handles all user-facing interactions, strict numeric menu loops, comprehensive form validation loops (regex name/email checks, headcount ranges, asset & description length constraints), clean timestamps (YYYY-MM-DD HH:MM:SS), and an interactive numbered image selection menu for the /images/ directory.
ai_manager.py: Integrates the official google-genai SDK targeting the Gemini flash model. Features automated JSON response parsing/cleaning, and robust error resilience for 503 network congestion and 429 quota exhaustion with intelligent offline fallbacks.
logic_manager.py: Core mathematical and decision-making engine. Computes weighted priority scores based on severity and impacted headcount, determines operational dispatch queues, checks for active duplicate submissions, and sorts records by severity.
data_manager.py: Manages persistent storage via a local JSON database (incidents_database.json) with directory initialization safety and permission checks, database clearing, keyword querying, status updating ("Pending Review" to "Resolved"), record deletion by ID, and a dedicated Excel export utility (export_safety_report.xlsx) for facilities management using openpyxl.
📊 System Execution Flow
The application follows a structured, sequential data pipeline across its modules from user input to persistent storage:
Initialization (main.py & io_manager.py):
main.py boots the application and loops through display_menu() to capture user actions.
Defensive Input Capture (io_manager.py ➔ main.py):
When a report is submitted, io_manager.py collects validated names, contacts, locations, image choices, and character-guarded descriptions, returning them as a dictionary to main.py.
AI Risk Assessment (main.py ➔ ai_manager.py):
main.py hands the record to ai_manager.py, which communicates with Gemini using multi-model fallback, retry backoffs, and offline JSON safeguards, returning structured JSON analysis.
Triage & Logic Processing (main.py ➔ logic_manager.py):
logic_manager.py computes priority scores, determines emergency vs. maintenance routing queues, checks for active duplicate submissions, and sorts records by severity.
Persistent Storage & Export (main.py ➔ data_manager.py):
data_manager.py assigns a sequential ID (INCIDENT-001), saves sorted records into incidents_database.json, or generates a professional Excel spreadsheet (export_safety_report.xlsx) via openpyxl.
User Output (io_manager.py):
io_manager.py renders final confirmation receipts, filtered search lists, or status update screens back to the console interface.
🛡️ Error Resilience & Cloud Fallback Architecture
To ensure high availability during third-party API congestion or rate limits, the system features a robust fault-tolerant pipeline:
Multi-Model Cascade: Automatically rotates between active flash model endpoints (gemini-3.8-flash -> gemini-3.6-flash) if an endpoint experiences traffic spikes.
Incremental Retry Backoff: Automatically handles transient 503 Service Unavailable or 429 Rate Limit errors with timed delay backoffs.
Intelligent Offline Fallback: If cloud endpoints remain unreachable or time out after 300 seconds, the manager seamlessly pivots to a structured JSON offline assessment mode, ensuring zero application crashes and continuous local functionality.
🛡️ Robust Input Validation & Safety Features
Strict Menu Navigation: Rejects non-numeric text, spaces, and out-of-range inputs (1-8), prompting the user cleanly until valid.
Reporter Name Verification: Enforces a regex check ensuring names contain letters and spaces only (no numbers or symbols).
Institutional Contact Verification: Validates formatting for official SIT student/staff email addresses (@sit.singaporetech.edu.sg) or standard 8–11 digit phone numbers.
Bounded Headcount Range: Restricts affected headcount numbers to a realistic campus range (1 to 1000).
Asset & Description Length Guards: Enforces minimum character requirements (at least 3 characters for assets, at least 15 characters for hazard descriptions) to ensure high-context AI analysis.
Interactive Image Selection: Scans the /images/ directory (handling extension case-sensitivity smoothly), allowing users to select visual evidence via a safe numeric menu with automated error loops.
🛠️ Prerequisites & Installation
Python Version: Ensure Python 3.8+ is installed on your machine.
Install Dependencies: Install the required official Google GenAI package, Excel generator library, and environment manager via pip:
pip install google-genai openpyxl python-dotenv
⚡️ Quick Start
Run the Application: Start the interactive console from your project root terminal:
python main.py
Run the Automated Test Suite: Verify core logic algorithms, severity sorting, routing, and AI response parsing:
python test_app.py
Configure Environment Variables:
Create a .env file in the root directory of your project folder and add your Google Gemini API key:
GEMINI_API_KEY=your_actual_api_key_here
