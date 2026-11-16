"""
e2e_tests/conftest.py
Ephemeral test environment fixtures, isolated SQLite database provisioning,
FastAPI TestClient, and WebSocket test harness.
"""

from __future__ import annotations
import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from starlette.testclient import TestClient

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend.config as config
import backend.database as database
import backend.auth as auth
from backend.app import app
from backend.services.serial_service import serial_service


@pytest.fixture(autouse=True)
def ephemeral_env() -> Generator[Path, None, None]:
    """
    Provisions an isolated temporary directory and SQLite database for every test.
    Guarantees that no test mutates or pollutes the production database or models.
    """
    temp_dir = tempfile.mkdtemp(prefix="iot_e2e_test_")
    temp_path = Path(temp_dir)
    temp_db_path = temp_path / "test_iot_anomaly.db"

    # Save original configurations
    orig_db_path_env = os.environ.get("DB_PATH")
    orig_pwd_env = os.environ.get("ADMIN_PASSWORD")
    orig_config_db_path = config.DB_PATH
    orig_config_pwd = config.ADMIN_PASSWORD
    orig_db_module_path = database.DB_PATH

    # Set ephemeral test environment
    os.environ["DB_PATH"] = str(temp_db_path)
    os.environ["ADMIN_PASSWORD"] = "TestAdminPassword123!"
    config.DB_PATH = temp_db_path
    config.ADMIN_PASSWORD = "TestAdminPassword123!"
    database.DB_PATH = temp_db_path
    database._initialized = False

    # Reset rate limiting dictionary
    auth._LOGIN_ATTEMPTS.clear()

    # Ensure clean database tables exist in temp db
    conn = database.get_db_connection()
    conn.close()

    yield temp_path

    # Teardown
    try:
        serial_service.stop_stream()
    except Exception:
        pass

    # Restore original configurations
    if orig_db_path_env is not None:
        os.environ["DB_PATH"] = orig_db_path_env
    else:
        os.environ.pop("DB_PATH", None)

    if orig_pwd_env is not None:
        os.environ["ADMIN_PASSWORD"] = orig_pwd_env
    else:
        os.environ.pop("ADMIN_PASSWORD", None)

    config.DB_PATH = orig_config_db_path
    config.ADMIN_PASSWORD = orig_config_pwd
    database.DB_PATH = orig_db_module_path
    database._initialized = False
    auth._LOGIN_ATTEMPTS.clear()

    # Force garbage collection to release open SQLite handles on Windows
    import gc
    gc.collect()

    # Remove temporary directory
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provides a synchronous FastAPI TestClient instance configured for boundary tests."""
    with TestClient(app, base_url="http://localhost:8000", raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def admin_password() -> str:
    """Default admin password used in ephemeral test runs."""
    return "TestAdminPassword123!"


@pytest.fixture
def admin_token(admin_password: str) -> str:
    """Generates a valid signed HMAC-SHA256 bearer token for admin routes."""
    return auth.generate_signed_token()


@pytest.fixture
def test_csv_path() -> Path:
    """Path to the authoritative labeled test dataset."""
    return PROJECT_ROOT / "data" / "processed" / "test_data_with_labels.csv"
