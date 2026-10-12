# Docker Guide

This guide explains how to build and run the Campus Safety Hazard Reporting System in Docker. The container runs the interactive CLI and the Streamlit facilities dashboard together.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

## Setup

### 1. Build the image

```bash
docker build -t hazard-reporter .
```

### 2. Run the container

**Windows PowerShell:**

```powershell
docker run -it --rm --init --env-file .env -p 8501:8501 -v hazard-data:/app/data -v hazard-uploads:/app/uploads -v "${PWD}/evidence:/evidence:ro" hazard-reporter
```

**macOS/Linux:**

```bash
docker run -it --rm --init --env-file .env -p 8501:8501 -v hazard-data:/app/data -v hazard-uploads:/app/uploads -v "$(pwd)/evidence:/evidence:ro" hazard-reporter
```

The CLI menu appears in your terminal.

### 3. Open the dashboard

The browser does not open automatically. Open your browser and visit:

**http://localhost:8501**

Allow a few seconds for Streamlit to start, then refresh if the page does not load.

## Attaching images

The container has no graphical file picker, so the CLI asks for an image path instead.

1. Place your hazard photo in the `evidence` folder in the project root.
2. When prompted, enter the path inside the container, for example:

   ```text
   /evidence/photo.jpg
   ```

## Data storage

Incident records, exports, private database backups and uploaded images are stored in Docker volumes, so they are kept between container runs.

| Volume | Contents |
| --- | --- |
| `hazard-data` | `hazardreportdb.json`, CSV/TXT exports and private `backups/` snapshots |
| `hazard-uploads` | Attached hazard images |

### Database backup and recovery

Before deleting an existing incident, `Data_Manager.py` creates a timestamped snapshot of the complete database under `/app/data/backups/`. If backup creation fails, deletion is cancelled. Up to 30 snapshots are kept. Backups persist in the `hazard-data` volume across container restarts.

Restoring a snapshot is supported through `Data_Manager.restore_backup()` in Python code, but there is no dashboard restoration button. No hourly backup scheduler is active. Backups may contain reporter details; treat them as private data and never commit them to Git.

**Warning:** Removing `hazard-data` removes the active database **and all backups**. To delete all stored data and start fresh:

```bash
docker volume rm hazard-data hazard-uploads
```

## Stopping the container

Select option `4` (Exit) in the CLI. This stops the CLI, the dashboard and the container together.

## Running tests in Docker

```bash
docker run --rm hazard-reporter python test_script.py
```

## Troubleshooting

| Problem | Solution |
| --- | --- |
| `Unable to find image 'hazard-reporter'` | Build the image first with `docker build -t hazard-reporter .` |
| `Missing expression after unary operator '--'` | You pasted a multi-line bash command into PowerShell. Use the single-line PowerShell command above. |
| Dashboard does not load | Check that `-p 8501:8501` is in your run command, and that nothing else (such as a local `python main.py`) is using port 8501. |
| Code changes are not showing | Rebuild the image with `docker build -t hazard-reporter .` |