"""
backend/schemas/admin_schemas.py
Pydantic schemas for authenticated admin management, model telemetry, and benchmarks.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    password: str = Field(..., description="Admin secret password from environment")


class AdminLoginResponse(BaseModel):
    token: str = Field(..., description="Signed expiring Bearer token")
    token_type: str = Field("bearer")
    expires_in_seconds: int


class ModelDetailsResponse(BaseModel):
    version: str = Field(..., description="Pipeline version")
    commit_hash: str = Field(..., description="Git commit hash of active weights")
    feature_cols: List[str] = Field(..., description="List of 12 input features")
    iforest_threshold: float = Field(..., description="Isolation forest decision threshold")
    sensitivity: str = Field(..., description="Active sensitivity preset")
    sensitivity_thresholds: Dict[str, float] = Field(...)
    normal_temp_mean: float
    normal_temp_std: float
    normal_hum_mean: float
    normal_hum_std: float


class BenchmarkMetricItem(BaseModel):
    dataset_name: str
    detector: str
    row_count: int
    event_count: int
    provenance: str = Field(..., description="Recorded or Synthetic")
    role: str = Field(..., description="Development or Held-out")
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float
    recall: float
    f1: float
    pr_auc: float
    roc_auc: float
    note: Optional[str] = None


class AuditLogItem(BaseModel):
    id: int
    timestamp: str
    action: str
    actor: str
    details: str


class AdminMetricsResponse(BaseModel):
    queue_depth: int = Field(..., description="Current pending messages across active WebSocket client queues")
    dropped_messages: int = Field(..., description="Total dropped messages due to client queue overflow")
    connected_clients: int = Field(..., description="Total connected WebSocket clients")
    reading_counts: int = Field(..., description="Total count of sensor readings stored in database")
    readings_count: Optional[int] = Field(None, description="Alias for reading_counts")
    details: Optional[Dict[str, Any]] = Field(None, description="Detailed queue and session diagnostics")


class RetentionSettingsResponse(BaseModel):
    retention_days: int = Field(..., description="Current retention window in days")


class RetentionSettingsUpdate(BaseModel):
    retention_days: int = Field(..., description="New retention window in days (must be >= 1)", ge=1)


class DatabasePurgeRequest(BaseModel):
    days: Optional[int] = Field(None, description="Purge readings older than this many days (must be >= 1)", ge=1)
    cutoff: Optional[str] = Field(None, description="Explicit ISO cutoff timestamp")


class DatabasePurgeResponse(BaseModel):
    purged_rows: int = Field(..., description="Number of purged records deleted from database")
