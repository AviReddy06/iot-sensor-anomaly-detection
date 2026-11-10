"""Shared pytest fixtures and path configuration."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def synthetic_steady_df() -> pd.DataFrame:
    """Create a calm, 2s-cadence synthetic baseline trace (200 rows)."""
    ts = pd.date_range("2026-11-10 10:00:00", periods=200, freq="2s")
    rng = np.random.default_rng(7)
    temp = np.round(28.0 + 0.05 * np.sin(np.linspace(0, 2, 200)) + rng.normal(0, 0.03, 200), 1)
    hum = np.round(58.0 + 0.2 * np.cos(np.linspace(0, 2, 200)) + rng.normal(0, 0.08, 200), 1)
    return pd.DataFrame({"timestamp": ts, "temperature": temp, "humidity": hum})
