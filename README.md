# 🛡️ Campus Safety Hazard Reporting System

**INF1103 · Team 4 · SIT Punggol Coast**

A modular Python campus hazard reporting application that lets students and staff submit facility hazards through a command-line interface (CLI). It uses Google Gemini to assess risk when available, applies rule-based priority and dispatch decisions, and stores completed incident records in a local JSON database. A separate Streamlit interface lets facilities staff review and manage incidents.

> **Project scope:** This is a prototype decision-support system. AI assessments and automated routing recommendations should be reviewed by authorised facilities personnel; the program does not itself dispatch an emergency response.

## 🎯 Project background and initial objectives

The original **Team 4 Project Initial Details** proposal identified a campus-safety problem: students and staff need a centralised way to report hazards such as electrical faults, leaks, and damaged facilities, while maintenance teams need structured information to prioritise cases and recognise recurring problems. This prototype focuses on turning those reports into records that can be assessed, prioritised, and reviewed.

### 👥 Intended users

| User group | Intended use |
| --- | --- |
| **Front-line reporters (students and teachers)** | Report facility and equipment hazards encountered in classrooms, laboratories, lecture theatres, and other campus locations. |
| **Maintenance teams and safety officers** | Review incoming incidents, identify higher-priority and recurring problems, and manage resolution progress. |

### 📝 Information collected

The original proposal specified five main inputs: **location**, **visual evidence**, **number of people affected**, **asset information**, and an **unstructured hazard description**. The implemented CLI also collects reporter name and contact details. Visual evidence is optional in the current application.

### 📌 Original goals and implementation status

| Proposed capability | Current implementation |
| --- | --- |
| Multimodal hazard submission | CLI accepts written report details and one optional PNG, JPEG or WebP image through a graphical picker or terminal path input when the GUI is unavailable. |
| AI risk summary, classification and assessment | Gemini is used to produce a risk summary, category, severity, operational impact, and contextual insights when available. |
| Historical patterns and duplicate detection | Rule-based comparisons identify prior incidents with matching location and asset details. |
| Deterministic priority and routing | Business rules calculate a score, recommend an action, and assign a queue label. |
| Human-in-the-loop oversight | Streamlit interface supports incident review and status changes; it does **not** currently offer an interface to edit AI category, severity, or routing recommendations. |
| Persist incident and dispatch | The system stores the incident and its recommended dispatch route locally; it does **not** automatically notify or dispatch a real maintenance or emergency team. |

**Design distinction:** The system generates the AI assessment and calculates hazard priority before asking the reporter to confirm submission. The reporter can review the assessment summary and either confirm or cancel. Only confirmed reports are saved to the JSON database.

## ✨ Features

- **📝 Guided hazard reporting:** Collects reporter details, location, estimated people affected, asset information, and a hazard description, with input validation.
- **📷 Optional image evidence:** Accepts PNG, JPEG and WebP images through a graphical file picker, with terminal-based path input when a graphical interface is unavailable. Images are saved in the `uploads/` directory using their original filenames. When a filename already exists, a numbered suffix (such as `_2` or `_3`) prevents overwriting.
- **🤖 AI risk assessment:** Requests a structured Gemini assessment containing category, severity, operational impact, risk summary, and contextual insights.
- **🛟 Offline fallback:** Creates a rule-based fallback assessment if Gemini is unavailable or returns an unusable response.
- **🚦 Priority and routing:** Calculates a priority score, recommends an action, and assigns a maintenance or urgent-dispatch queue label.
- **🔎 Recurring-hazard checks:** Compares new reports with historical records to identify repeated location/asset combinations and potential duplicates.
- **🗃️ Incident history:** Saves each completed report, including the original inputs, assessment, decision, ID, timestamp, and status, in `hazardreportdb.json`.
- **🗂️ Backups before deletion:** Before removing an existing incident, Data Manager saves a timestamped snapshot of the complete JSON database. If the backup cannot be created, deletion is cancelled. Up to 30 recent backups are retained in a private `backups/` folder.
- **🖥️ Facilities management UI:** Provides a Streamlit dashboard for incident review, status updates, deletion, and CSV/TXT exports.
- **🔄 Automatic dashboard refresh:** A Streamlit fragment reloads incident records approximately every 2 seconds, allowing CLI submissions and management changes to appear without manually refreshing the page.
- **📄 Readable TXT reports:** The improved export generates separate, labelled sections for each incident instead of CSV-formatted text.

## 📁 Project structure

```text
.
├── main.py                       # CLI entry point and workflow orchestration
├── IO_Manager.py                 # Console menus, validation and image selection
├── ai_manager.py                 # Gemini requests, JSON parsing and validation
├── logic_manager.py              # Fallback, scoring, duplicates and routing
├── Data_Manager.py               # Incident storage, backup/restore and exports
├── management_ui.py              # Streamlit incident management dashboard
├── test_script.py                # 35 procedural offline automated tests
├── requirement.txt               # Python dependencies (singular filename)
├── Dockerfile                    # Python 3.12 container configuration
├── .dockerignore                 # Excludes secrets/data from Docker build context
├── DOCKER.md                     # Docker build, run and troubleshooting guide
├── .github/                      # GitHub Actions configuration
│   └── workflows/
│       └── ci.yml                # Automated Python and Docker CI pipeline
├── .gitignore                    # Git exclusions
└── README.md

Generated locally (keep private; ensure these are excluded from Git tracking):
├── .env                          # Private Gemini API key; never commit
├── hazardreportdb.json           # Local incident database
├── backups/                      # Private JSON database snapshots
├── uploads/                      # Optional hazard image attachments
├── evidence/                     # Optional local Docker image inputs (keep private)
├── hazard_reports.csv            # Generated CSV export
└── hazard_reports.txt            # Generated TXT export
```

`hazardreportdb.json` may initially be absent; Data Manager treats a missing database as empty and creates it when the first report is saved. A clean `[]` JSON database can be included separately in the school's ZIP submission. Do not publish real reporter details, incident images, API keys or export files containing personal information.

## 🔄 How the system works

```mermaid
flowchart TD
    A[CLI: submit new hazard] --> B[IO_Manager: validate input and optional image]
    B --> C[main: prepare record and load history]
    C --> D[ai_manager via logic_manager: Gemini assessment]
    D --> E{Valid Gemini assessment?}
    E -->|Yes| F[Structured risk assessment]
    E -->|No| G[Offline fallback assessment]
    F --> H[logic_manager: frequency, duplicate, score and routing]
    G --> H
    H --> P[IO_Manager: show assessment and priority summary]
    P --> Q{Reporter confirms submission?}
    Q -->|No| X[Cancel without saving]
    Q -->|Yes| I[Data_Manager: assign ID and save complete record]
    I --> J[(hazardreportdb.json)]
    J --> K[CLI incident views]
    J --> L[Streamlit management UI]
    L --> M[Status updates, deletion and CSV/TXT export]
```

The application processes a report in this order:

1. **Input:** `IO_Manager.py` gathers and validates reporter details and optional evidence.
2. **Assessment:** `main.py` passes the record into `logic_manager.process_record()`, which calls `ai_manager.py` for Gemini processing and uses an offline assessment if necessary.
3. **Business rules:** `logic_manager.py` checks historical frequency and potential duplicates, calculates a priority score, and selects a recommended action and route.
4. **Confirmation:** `IO_Manager.py` presents the assessment and recommended action; the reporter chooses whether to save or cancel.
5. **Storage:** For confirmed submissions, `Data_Manager.py` assigns an `INCIDENT-001`-style identifier and persists the complete incident in `hazardreportdb.json`.
6. **Review:** The CLI displays reports and frequent hazards; `management_ui.py` supports facilities review and incident management.

## 🧩 Modules and responsibilities

| File | Responsibility |
| --- | --- |
| `main.py` | Coordinates input, AI assessment, business-rule evaluation, persistence, and CLI navigation; launches Streamlit as a subprocess. |
| `IO_Manager.py` | Displays the four-option CLI menu, validates reporter input, and uses Tkinter for optional image selection with a terminal fallback when no GUI is available. |
| `ai_manager.py` | Builds the Gemini prompt, attaches supported image content, calls configured models, parses JSON, and validates expected response fields. |
| `logic_manager.py` | Handles offline fallback, scoring, historical frequency, potential-duplicate detection, priority decisions, and routing. |
| `Data_Manager.py` | Loads and saves the local JSON database, generates incident IDs, updates and deletes records, takes pre-deletion backups, supports programmatic restoration, and exports CSV/TXT files. |
| `management_ui.py` | Shows a Streamlit incident table and details, uses `Data_Manager.load()` for incident data, enables status changes and deletion, and provides exports, with an approximately 2-second automatic refresh. |
| `test_script.py` | Runs 35 procedural offline automated tests, including mocked Gemini requests, historical-frequency checks and backup-failure protection. |

## ✅ Prerequisites

- **Python 3.10 or newer** (the updated Streamlit dashboard uses union type annotations such as `list[dict[str, Any]] | None`).
- `pip` and access to install Python dependencies.
- **Docker Desktop / Docker Engine** for the optional container build and demonstration.
- A graphical environment with Tkinter for the native image picker; where unavailable, the CLI accepts an image file path instead.
- A Gemini API key for live AI analysis. Without a usable key or service, the normal submission workflow uses an offline fallback assessment.

## 🛠️ Installation

1. Clone the repository and enter the project directory:

   ```bash
   git clone https://github.com/2603229/INF1103_P3_T4.git
   cd INF1103_P3_T4
   ```

2. (Recommended) Create and activate a virtual environment:

   **Windows PowerShell:**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS/Linux:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies from the provided file:

   ```bash
   python -m pip install -r requirement.txt
   ```

4. Create a local `.env` file in the project root:

   ```dotenv
   GEMINI_API_KEY=replace_with_your_gemini_api_key
   ```

   Keep `.env` private. It is excluded by the supplied `.gitignore`. Never place a real API key in the README or a Git commit.

## ▶️ Running the application

Start the combined CLI + management UI using:

```bash
python main.py
```

The CLI offers four options:

| Option | Action |
| --- | --- |
| `1` | Submit New Hazard Report |
| `2` | View All Logged Incidents |
| `3` | View Top 5 Most Frequent Hazards |
| `4` | Exit |

`main.py` also starts Streamlit in a subprocess. To run **only** the facilities management dashboard, use:

```bash
python -m streamlit run management_ui.py
```

Streamlit is typically available locally at `http://localhost:8501`. When launched from `main.py`, its terminal output is suppressed, so open that address manually if necessary. The dashboard shows a message when the database is missing or empty and rechecks it automatically. Exiting the CLI shuts down the Streamlit subprocess in the updated `main.py`.

### 📋 Submitting a report

Choose option `1` and enter the requested reporter name, SIT email or Singapore phone number, location, estimated affected headcount, asset summary, and detailed description. Optionally attach a PNG, JPEG or WebP image through the file picker or terminal path input if the GUI is unavailable. The application assesses the report, checks historical records, determines priority and routing, and presents a pre-submission summary. It saves the complete report only after the reporter confirms.

The current input checks include:

- A reporter name using supported letters and punctuation.
- An `@sit.singaporetech.edu.sg` email or a validated eight-digit phone number.
- A nonempty location.
- An affected headcount from **1 to 1,000**.
- An asset summary of at least **3 characters**.
- A hazard description of at least **15 characters**.

## 🐳 Docker Deployment

The Campus Safety Hazard Reporting System includes Docker configuration for consistent deployment. The Docker image uses **Python 3.12**, installs dependencies from `requirement.txt`, and runs the interactive CLI (`main.py`) together with the Streamlit facilities dashboard on port **8501**.

### Prerequisites

Install Docker Desktop (Windows/macOS) or Docker Engine (Linux) and ensure the Docker service is running.

### Build the Docker image

From the project root:

```bash
docker build -t hazard-reporter .
```

### Run automated tests in Docker

Run the procedural offline tests inside the image:

```bash
docker run --rm hazard-reporter python test_script.py
```

**Docker verification (12 October 2026):** The updated `hazard-reporter` image built successfully, and all **35 procedural automated tests passed locally and inside Docker**, with zero failures, errors or skipped tests (AI: 14; Logic: 10; Data: 6; IO: 3; Main: 2). Earlier interactive checks on 11 October verified the CLI, a live Gemini assessment, recovery from HTTP 504, incident saving and JSON persistence after restart. Team members should still test the image on their own machines before submission.

### Run the CLI and dashboard

In **Windows PowerShell** (or a macOS/Linux terminal), from the project root with a private `.env` file:

```powershell
docker run -it --rm --init --env-file .env -p 8501:8501 -v hazard-data:/app/data -v hazard-uploads:/app/uploads hazard-reporter
```

The four-option CLI opens in the terminal. Visit **http://localhost:8501** to use the Streamlit dashboard. Select **option 4** in the CLI to exit. If you are testing only the offline fallback without an `.env` file, omit `--env-file .env`.

### Persistent data storage

The container uses named Docker volumes to preserve application data between container runs:

| Volume | Container directory | Stored content |
| --- | --- | --- |
| `hazard-data` | `/app/data` | `hazardreportdb.json`, CSV/TXT exports and private `backups/` snapshots |
| `hazard-uploads` | `/app/uploads` | Attached hazard images |

Within Docker, `HAZARD_DATA_DIR=/app/data` ensures `Data_Manager.py` stores incident data and its `backups/` folder in the mounted volume. The database is created when the first confirmed incident is saved if it does not already exist. Backups survive container restarts but are deleted if the `hazard-data` volume is removed.

### Optional image attachments

Docker runs without a graphical file picker, so the CLI accepts an image path instead. Place supported images in a local `evidence/` folder, mount the folder read-only when running the container, and enter the container path such as `/evidence/photo.jpg` when prompted. See [`DOCKER.md`](DOCKER.md) for the full Windows and macOS/Linux commands.

### Security

The `.dockerignore` file keeps the private `.env`, local incident database, `backups/`, exports, uploaded images, local `evidence/` and Python caches out of the Docker build context. The `.gitignore` file separately excludes local credentials and incident data (including backups) from future Git tracking. Confirm the ignore rules before committing.

Never publish real API keys, reporter contact details, or incident images. Keeping files out of future commits does not erase them from earlier Git history.

### Docker documentation and CI/CD status

See [`DOCKER.md`](DOCKER.md) for build/run commands, evidence mounting, volumes, shutdown and troubleshooting. Docker image building, automated testing, and persistence have been verified. GitHub Actions continuous integration is also configured and verified, as described below.

## 🔄 Continuous Integration (GitHub Actions)

The project uses GitHub Actions for **continuous integration (CI)**. The workflow is defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) and runs on pushes, pull requests, and manual dispatch.

### CI pipeline

The pipeline runs on **Ubuntu 24.04** with **Python 3.12** and automatically:

1. Checks out the repository.
2. Sets up Python and installs dependencies from `requirement.txt`.
3. Verifies Python syntax.
4. Runs the current **35 offline automated tests**.
5. Builds the `hazard-reporter` Docker image.
6. Runs the **35 tests again inside Docker**.

Gemini API calls are mocked in the automated tests, so no live API key is required for CI.

### Verified workflow run

| Item | Verified result |
| --- | --- |
| Workflow | INF1103 Team 4 CI Pipeline |
| Run | #2 |
| Date | 11 October 2026 |
| Branch | `main` |
| Commit | `75e3244` |
| Status | **Success** |
| Total duration | 1 minute 10 seconds |

[View GitHub Actions runs](https://github.com/2603229/INF1103_P3_T4/actions).

This workflow provides automated **CI verification**; automatic deployment to a production server is not configured. Subsequent pushes should continue to pass the checks.

## 🤖 AI assessment and fallback

The Gemini response is expected to contain these five string fields:

| Field | Expected content |
| --- | --- |
| `risk_summary` | Concise safety risk summary |
| `category` | `Electrical`, `Plumbing`, `Structural`, `HVAC`, or `IT/Equipment` |
| `severity` | `Low`, `Medium`, `High`, or `Critical` |
| `operational_impact` | `Minor`, `Moderate`, `Severe`, or `Catastrophic` |
| `contextual_insights` | Explanation and relevant safety considerations |

`ai_manager.py` uses the official Google GenAI SDK to request a structured JSON hazard assessment. The configured model candidates are `gemini-3.8-flash` and `gemini-3.6-flash`. A live request to `gemini-3.8-flash` succeeded during the Docker demonstration on 11 October 2026; availability of each model still depends on the configured API account.

Each HTTP request is configured with a **60-second timeout**. The application handles rate-limit errors (429), retries some temporary failures (such as 503), and switches between configured models where appropriate. The timeout applies **per HTTP request**, not to the entire assessment workflow; retries and model fallback can extend total processing time.

If the API is unavailable or returns an invalid assessment, the system generates a **provisional offline fallback** for human review. Its category can differ from the five allowed Gemini categories. A fallback triggered by an attached image **does not mean the image was analysed**. All assessments and routing recommendations require verification by authorised facilities personnel.

## 🚦 Priority and incident management

The Logic Manager calculates priority using three factors: **severity**, **operational impact**, and **historical frequency**. Severity contributes 1 (Low), 2 (Medium), 4 (High), or 5 (Critical) points. Operational impact contributes 1 (Minor), 2 (Moderate), 4 (Severe), or 5 (Catastrophic) points. Historical frequency adds 0–3 points based on matching incidents at the same location and asset that have a **Resolved** or **Closed** status; unresolved incidents are checked separately for potential duplicates.

The total score and business rules determine **Normal**, **High**, or **Critical** priority, along with a recommended action. The `route(record)` function assigns the appropriate maintenance or urgent-dispatch **queue label** based on the evaluated priority; it does not dispatch personnel. Duplicate detection flags matching unresolved incidents. `Resolved` and `Closed` reports are excluded from active duplicate checks but still count toward historical frequency.

Each saved record includes an incident identifier, timestamp, reporter input, assessment source, assessment fields, duplicate/frequency information, score, recommended action, assigned route, and status. Data is stored in the local `hazardreportdb.json` file.

In the Streamlit dashboard, facilities staff can view incidents sorted by score, inspect assessment details and image evidence where available, change a status among **Pending Review**, **In Progress**, **Resolved**, and **Closed**, delete a record after confirmation, and export incident records to **CSV** or **readable TXT**. A deletion creates a complete database backup first; the incident is not removed if backup creation fails. The dashboard uses `@st.fragment(run_every="2s")` to reload data periodically. Status updates and deletions trigger an immediate fragment rerun. Generated downloads are retained in Streamlit session state so the download buttons remain available across automatic refreshes.

### Database backup and recovery

`Data_Manager.delete_incident_by_id()` creates a timestamped `incidents_backup_*.json` snapshot **before** deleting an existing incident. The snapshot contains the entire database at that moment, including the incident that will be deleted. Backup creation must succeed before the deletion is saved. A maximum of **30 snapshots** is retained in `backups/`, beside the database file. These files may include private reporter details and must not be committed or shared.

`Data_Manager.list_backups()` lists stored snapshots, and `Data_Manager.restore_backup()` can restore a snapshot **programmatically**, after creating a safety backup of the current database. The Streamlit dashboard does not currently offer a restore button. Hourly backup scheduling is not active; the implemented automatic trigger is incident deletion. Status updates and full-database clearing do not trigger this backup-before-deletion process.

## ⚙️ Configuration and data files

| Setting | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | API key used by `ai_manager.py` for Gemini requests. |
| `INCIDENTS_DB` | Optional override for the JSON database location used by `Data_Manager.py` and the Streamlit UI. |
| `HAZARD_DATA_DIR` | Optional data directory for `Data_Manager.py` when `INCIDENTS_DB` is not set. |

**Database management:** Incident database reads and writes are centralised in `Data_Manager.py`. Both the main CLI and Streamlit management dashboard retrieve incidents through Data Manager. By default, records are stored in `hazardreportdb.json`. The `INCIDENTS_DB` and `HAZARD_DATA_DIR` environment variables allow alternate storage paths.

## 🧪 Automated Testing

The project includes `test_script.py`, containing **35 procedural offline automated tests** without class definitions.

| Test area | What is covered |
| --- | --- |
| AI Manager | Prompt creation, response validation, JSON parsing, and mocked API requests |
| Logic Manager | Priority scoring, evaluation, historical-frequency filtering, duplicate detection, and fallback behaviour |
| Data Manager | Database load/save, IDs, status updates, backup-before-deletion and simulated backup-failure protection, and malformed JSON handling |
| IO Manager | Submission confirmation input handling |
| Main workflow | Saving confirmed reports and not saving cancelled reports |

Run from the project root:

```bash
python test_script.py
```

For individual test results, or to run without database tests:

```bash
python test_script.py --details
python test_script.py --no-data
```

Gemini calls are mocked so the test suite does **not** require a live API key or network access. Data Manager tests use temporary JSON files to avoid changing the actual incident database. On **12 October 2026**, all **35 tests passed locally and inside Docker**, with zero failures, errors or skipped tests. The tests include backup-before-deletion and simulated backup failure; they do **not** directly exercise restoration. The historical GitHub Actions CI run #2 (11 October 2026, commit `75e3244`) verified the earlier version; confirm the workflow for the latest pushed commit before claiming the updated CI run succeeded. Streamlit operations and optional image attachments should also be checked manually; the CLI, a live Gemini assessment and incident persistence were verified during an earlier Docker demonstration.

## 👥 Created By

🎓 **INF1103 – Programming Fundamentals with DevOps**  
🏫 **Team 4 | Singapore Institute of Technology (SIT)**

### 👨‍💻 Team Members

- CHAN RUI RU
- CHEE BO YU
- KOH KA-WEI DARRYL
- CHUA QIN NI JAMIE
- KHUN AUNG HEIN
- CHIA SENG CHAN

## 🔗 Repository

[INF1103 Team 4 – GitHub](https://github.com/2603229/INF1103_P3_T4)