"""
backend/schemas/health_schemas.py
Pydantic schemas for /api/health observability reporting.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall health: healthy, degraded, or unhealthy")
    serial_state: str = Field(..., description="Serial connection state: connected, disconnected, simulating, offline, fault")
    last_reading_age_seconds: Optional[float] = Field(None, description="Age in seconds of latest sensor reading")
    database_status: str = Field(..., description="Database connection status: connected, locked, error")
    model_version: str = Field(..., description="Active anomaly detection model version")
    commit_hash: str = Field(..., description="Git commit hash")
    uptime_seconds: float = Field(..., description="Uptime of the application in seconds")
    details: Optional[str] = Field(None, description="Diagnostic details or degraded reason")
    warning: Optional[str] = Field(None, description="Suspected fault or operational warning")
