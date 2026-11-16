"""
backend/config.py
Configuration loader for the IoT anomaly detection full-stack backend.
Reads parameters from the environment with robust defaults.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List

# Root project directory
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Database file location
DEFAULT_DB_PATH: Path = PROJECT_ROOT / "data" / "iot_anomaly.db"
DB_PATH: Path = Path(os.environ.get("DB_PATH", str(DEFAULT_DB_PATH)))

# Admin password from environment (None if unset)
ADMIN_PASSWORD: str | None = os.environ.get("ADMIN_PASSWORD")

# Serial port configuration (default "auto")
SERIAL_PORT: str = os.environ.get("SERIAL_PORT", "auto")

# Allowed HTTP origins for CORS
ALLOWED_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://.*\.streamlit\.app$"
ALLOWED_ORIGINS: List[str] = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Streamlit Cloud will be added via environment variable
]
# Additional origins from environment variable (comma-separated)
EXTRA_ALLOWED_ORIGINS: List[str] = [
    origin.strip() for origin in os.environ.get("EXTRA_ALLOWED_ORIGINS", "").split(",") if origin.strip()
]

# Device ingestion token for remote ESP32 telemetry
# Use a function to get the current value from environment at request time
def get_device_ingest_token() -> Optional[str]:
    """Get the device ingestion token from environment variable."""
    return os.environ.get("DEVICE_INGEST_TOKEN")


# Backward compatibility - module-level constant for backward compatibility
DEVICE_INGEST_TOKEN: str | None = os.environ.get("DEVICE_INGEST_TOKEN")
