# ============================================================
# INF1103 Team 4 - Campus Safety Hazard Reporting System
#
# Runs the interactive CLI (main.py). main.py also launches the
# Streamlit management dashboard as a subprocess on port 8501.
#
# Build:  docker build -t hazard-reporter .
# Run:    docker run -it --rm --init --env-file .env -p 8501:8501 \
#           -v hazard-data:/app/data -v hazard-uploads:/app/uploads \
#           hazard-reporter
# ============================================================

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Data_Manager stores hazardreportdb.json and CSV/TXT exports here
    HAZARD_DATA_DIR=/app/data \
    # Streamlit settings, read from the environment by the subprocess
    # that main.py starts, so main.py needs no changes
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install dependencies first so this layer is cached between code changes
COPY requirement.txt .
RUN pip install -r requirement.txt

# Application source
COPY *.py ./

# Run as a non-root user; data and uploads are writable volume mount points
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data /app/uploads \
    && chown -R appuser:appuser /app/data /app/uploads
USER appuser

# Streamlit management dashboard
EXPOSE 8501

# Persist the incident database, exports and attached images
VOLUME ["/app/data", "/app/uploads"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=4)" || exit 1

# Interactive CLI + dashboard. Requires `docker run -it`.
CMD ["python", "main.py"]
