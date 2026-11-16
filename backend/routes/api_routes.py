"""
backend/routes/api_routes.py
REST API endpoints for IoT Anomaly Detection backend.
"""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field
import hmac
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.inference_service import inference_service
from backend.services.serial_service import serial_service
import backend.config as backend_config

router = APIRouter(prefix="/api", tags=["API"])


# Pydantic Schemas
class ThresholdUpdateRequest(BaseModel):
    if_threshold: Optional[float] = None
    ewma_threshold: Optional[float] = None
    zscore_threshold: Optional[float] = None
    sensitivity_label: Optional[str] = None


class SerialStartRequest(BaseModel):
    port: str = "COM19"
    baud: int = 115200


class SimulationStartRequest(BaseModel):
    dataset_name: str = "eval_suite"
    interval_sec: float = 1.0


class AlertConfigRequest(BaseModel):
    enabled: Optional[bool] = None
    building_zone: Optional[str] = None
    min_severity: Optional[str] = None
    cooldown_sec: Optional[float] = None
    recovery_sec: Optional[float] = None
    ntfy_enabled: Optional[bool] = None
    ntfy_topic: Optional[str] = None
    webhook_enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    email_enabled: Optional[bool] = None
    email_from: Optional[str] = None
    email_to: Optional[List[str]] = None


class TelemetryIngestRequest(BaseModel):
    timestamp: Optional[str] = None
    temperature: float = Field(..., ge=-10.0, le=65.0)
    humidity: float = Field(..., ge=0.0, le=100.0)


# Endpoints
@router.get("/status")
def get_system_status() -> Dict[str, Any]:
    """Return overall system health, streaming state, and model details."""
    serial_status = serial_service.get_status()
    model_info = inference_service.get_model_info()
    return {
        "status": "online",
        "serial": serial_status,
        "model": {
            "type": model_info["model_type"],
            "active_sensitivity": model_info["thresholds"]["active_sensitivity"],
            "if_threshold": model_info["thresholds"]["iforest_threshold"],
            "ewma_threshold": model_info["thresholds"]["ewma_zscore_threshold"],
        },
        "incidents_count": len(serial_service.incident_log),
    }


@router.get("/models/info")
def get_models_info() -> Dict[str, Any]:
    """Return model hyperparameters, feature names, and thresholds."""
    return inference_service.get_model_info()


@router.get("/models/benchmarks")
def get_evaluation_benchmarks() -> Dict[str, Any]:
    """Return comprehensive evaluation benchmarks across all internal and external datasets."""
    summary_path = PROJECT_ROOT / "models" / "evaluation_summary.json"
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="evaluation_summary.json not found")
    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/thresholds/update")
def update_thresholds(req: ThresholdUpdateRequest) -> Dict[str, Any]:
    """Update runtime detection thresholds."""
    updated = inference_service.set_thresholds(
        if_threshold=req.if_threshold,
        ewma_threshold=req.ewma_threshold,
        zscore_threshold=req.zscore_threshold,
        sensitivity_label=req.sensitivity_label,
    )
    return {"status": "success", "thresholds": updated}


# Serial & Hardware
@router.get("/serial/ports")
def get_serial_ports() -> List[Dict[str, Any]]:
    """List available USB COM ports."""
    return serial_service.list_ports()


@router.post("/serial/start")
def start_serial_stream(req: SerialStartRequest) -> Dict[str, Any]:
    """Connect to ESP32 over serial and start streaming."""
    return serial_service.start_serial_stream(port=req.port, baud=req.baud)


@router.post("/serial/stop")
def stop_stream() -> Dict[str, Any]:
    """Stop active serial or simulated stream."""
    return serial_service.stop_stream()


@router.post("/simulation/start")
def start_simulation(req: SimulationStartRequest) -> Dict[str, Any]:
    """Replay historical dataset as a simulated live stream."""
    return serial_service.start_simulation(dataset_name=req.dataset_name, interval_sec=req.interval_sec)


@router.post("/simulation/stop")
def stop_simulation() -> Dict[str, Any]:
    """Stop simulation."""
    return serial_service.stop_stream()


# Device Telemetry Ingestion
class TelemetryIngestRequest(BaseModel):
    timestamp: Optional[str] = None
    temperature: float = Field(..., ge=-10.0, le=65.0)
    humidity: float = Field(..., ge=0.0, le=100.0)


@router.post("/telemetry/ingest")
async def ingest_telemetry(
    request: Request,
    payload: TelemetryIngestRequest,
) -> Dict[str, Any]:
    """
    Ingest remote device telemetry (temperature/humidity) from ESP32 or other devices.
    Authenticated via X-Device-Token header matching DEVICE_INGEST_TOKEN environment variable.
    """
    # Verify device token (read from environment at request time)
    device_token = backend_config.get_device_ingest_token()
    if not device_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device ingestion not configured: DEVICE_INGEST_TOKEN not set",
        )
    
    # Extract token from header
    provided_token = request.headers.get("X-Device-Token")
    if not provided_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Device-Token header",
        )
    
    # Constant-time comparison
    if not hmac.compare_digest(provided_token, backend_config.get_device_ingest_token() or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device token",
        )
    
    # Validate and use timestamp
    timestamp = payload.timestamp or datetime.now(timezone.utc).isoformat()
    temperature = payload.temperature
    humidity = payload.humidity
    
    # Validate sensor values
    if not (-10.0 <= payload.temperature <= 65.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Temperature must be between -10.0 and 65.0 Celsius",
        )
    if not (0.0 <= payload.humidity <= 100.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Humidity must be between 0.0 and 100.0 percent",
        )
    
    # Ingest the telemetry through the serial service's remote ingestion method
    result = serial_service.ingest_remote_telemetry(
        timestamp=timestamp,
        temperature=payload.temperature,
        humidity=payload.humidity,
    )
    
    return {
        "status": "success",
        "message": "Telemetry ingested successfully",
        "timestamp": timestamp,
        "temperature": temperature,
        "humidity": humidity,
        "source": "remote",
    }


# Removed duplicate TelemetryIngestRequest definition (moved above)
def get_recent_telemetry() -> List[Dict[str, Any]]:
    """Return recent scored telemetry frames for fast initial UI hydration."""
    return list(serial_service.scored_history)


@router.get("/incidents")
def get_recent_incidents() -> List[Dict[str, Any]]:
    """Return list of recent detected anomaly incidents."""
    return list(serial_service.incident_log)


# Datasets & Analytics
@router.get("/datasets")
def list_datasets() -> List[Dict[str, Any]]:
    """List available local evaluation and benchmark datasets."""
    return [
        {
            "id": "eval_suite",
            "name": "Unseen Multi-Fault + Live Hardware Suite",
            "description": "1,947 feature rows combining Nov 1 holdout, 6 controlled fault categories, and Nov 10 live COM19 data",
            "rows": 1947,
            "anomalies": 143,
        },
        {
            "id": "pilot",
            "name": "Physical Pilot Recording (Full Recovery)",
            "description": "3,084 feature rows across 2 physical heat/breath disturbance events with extended recovery tails",
            "rows": 3084,
            "anomalies": 503,
        },
        {
            "id": "test",
            "name": "Legacy Hold-Out Test Set",
            "description": "55 feature rows with a single 10-row thermal spike (22:03:29 to 22:03:47)",
            "rows": 55,
            "anomalies": 10,
        },
    ]


@router.get("/datasets/{name}")
def get_dataset_analysis(name: str, request: Request) -> Dict[str, Any]:
    # Check for path traversal attempts in raw path
    raw_path = request.url.path
    if ".." in raw_path or raw_path.count("/") > 3:
        raise HTTPException(status_code=400, detail="Invalid dataset name")
    """Load and process a dataset, returning all time-series points, anomaly flags, and metrics."""
    file_map = {
        "eval_suite": PROJECT_ROOT / "data" / "processed" / "eval_test_suite.csv",
        "pilot": PROJECT_ROOT / "data" / "processed" / "pilot_data_prepared.csv",
        "test": PROJECT_ROOT / "data" / "processed" / "test_data_with_labels.csv",
    }
    if name not in file_map:
        raise HTTPException(status_code=404, detail="Dataset not found")

    path = file_map[name]
    if not path.exists():
        if name == "pilot":
            path = PROJECT_ROOT / "data" / "raw" / "pilot_data.csv"
        else:
            raise HTTPException(status_code=404, detail=f"File {path.name} not found")

    df = pd.read_csv(path)

    # Attach verified annotations if pilot
    if name == "pilot" and (PROJECT_ROOT / "data" / "processed" / "pilot_event_annotations.csv").exists():
        ann = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "pilot_event_annotations.csv")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["label"] = 0
        for _, r in ann.iterrows():
            m = (df["timestamp"] >= pd.to_datetime(r["start_time"])) & (df["timestamp"] <= pd.to_datetime(r["end_time"]))
            df.loc[m, "label"] = 1

    processed_df, summary = inference_service.process_dataframe(df)

    # Convert DataFrame to JSON-serializable list of records
    records = []
    for _, row in processed_df.iterrows():
        rec = {
            "timestamp": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"]),
            "temperature": float(row["temperature"]),
            "humidity": float(row["humidity"]),
            "temp_ewma_residual": float(row["temp_ewma_residual"]),
            "hum_ewma_residual": float(row["hum_ewma_residual"]),
            "temp_rate": float(row["temp_rate"]),
            "hum_rate": float(row["hum_rate"]),
            "iforest_score": float(row["iforest_score"]),
            "iforest_anomaly": bool(row["iforest_anomaly"]),
            "ewma_z_score": float(row["ewma_z_score"]),
            "ewma_z_anomaly": bool(row["ewma_z_anomaly"]),
            "hybrid_anomaly": bool(row["hybrid_anomaly"]),
            "hybrid_score": float(row["hybrid_score"]),
        }
        if "label" in row:
            rec["ground_truth"] = int(row["label"])
        if "fault_type" in row:
            rec["fault_type"] = str(row["fault_type"])
        records.append(rec)

    # Per fault breakdown if available
    breakdown = {}
    if "fault_type" in processed_df.columns and "label" in processed_df.columns:
        for ft, grp in processed_df.groupby("fault_type"):
            is_pos = int(grp["label"].iloc[0]) == 1
            breakdown[ft] = {
                "rows": len(grp),
                "is_fault": is_pos,
                "if_detected": int(grp["iforest_anomaly"].sum()),
                "ewma_detected": int(grp["ewma_z_anomaly"].sum()),
                "hybrid_detected": int(grp["hybrid_anomaly"].sum()),
                "hybrid_rate": round(float(grp["hybrid_anomaly"].mean() * 100), 1),
            }

    return {
        "dataset_id": name,
        "summary": summary,
        "fault_breakdown": breakdown,
        "rows": records,
    }


@router.post("/datasets/upload")
async def upload_custom_dataset(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload custom CSV, compute 12 features, run all detectors, and return scored analysis."""
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {exc}")

    # Validate schema - must have required columns
    required_cols = {"timestamp", "temperature", "humidity"}
    if not required_cols.issubset(df.columns):
        raise HTTPException(
            status_code=400,
            detail="CSV must contain 'timestamp', 'temperature', and 'humidity' columns."
        )

    processed_df, summary = inference_service.process_dataframe(df)

    records = []
    for _, row in processed_df.iterrows():
        records.append({
            "timestamp": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"]),
            "temperature": float(row["temperature"]),
            "humidity": float(row["humidity"]),
            "temp_ewma_residual": float(row["temp_ewma_residual"]),
            "hum_ewma_residual": float(row["hum_ewma_residual"]),
            "temp_rate": float(row["temp_rate"]),
            "hum_rate": float(row["hum_rate"]),
            "iforest_score": float(row["iforest_score"]),
            "iforest_anomaly": bool(row["iforest_anomaly"]),
            "ewma_z_score": float(row["ewma_z_score"]),
            "ewma_z_anomaly": bool(row["ewma_z_anomaly"]),
            "hybrid_anomaly": bool(row["hybrid_anomaly"]),
            "hybrid_score": float(row["hybrid_score"]),
        })

    return {
        "filename": file.filename,
        "summary": summary,
        "rows": records,
    }


# Alerts Management
@router.get("/alerts/config")
def get_alerts_config() -> Dict[str, Any]:
    """Get active alerting configuration."""
    s = serial_service.alert_manager.settings
    return {
        "enabled": s.enabled,
        "building_zone": s.building_zone,
        "min_severity": s.min_severity,
        "cooldown_sec": s.cooldown_sec,
        "recovery_sec": s.recovery_sec,
        "active_channels": s.active_channels(),
        "ntfy": {"enabled": s.ntfy_enabled, "server": s.ntfy_server, "topic": s.ntfy_topic},
        "webhook": {"enabled": s.webhook_enabled, "configured": bool(s.webhook_url)},
        "email": {"enabled": s.email_enabled, "from": s.email_from, "recipients": s.email_to},
    }


@router.post("/alerts/config")
def update_alerts_config(req: AlertConfigRequest) -> Dict[str, Any]:
    """Update alert settings dynamically."""
    s = serial_service.alert_manager.settings
    if req.enabled is not None:
        s.enabled = req.enabled
    if req.building_zone is not None:
        s.building_zone = req.building_zone
    if req.min_severity is not None:
        s.min_severity = req.min_severity
    if req.cooldown_sec is not None:
        s.cooldown_sec = req.cooldown_sec
    if req.recovery_sec is not None:
        s.recovery_sec = req.recovery_sec
    if req.ntfy_enabled is not None:
        s.ntfy_enabled = req.ntfy_enabled
    if req.ntfy_topic is not None:
        s.ntfy_topic = req.ntfy_topic
    if req.webhook_enabled is not None:
        s.webhook_enabled = req.webhook_enabled
    if req.webhook_url is not None:
        s.webhook_url = req.webhook_url
    if req.email_enabled is not None:
        s.email_enabled = req.email_enabled
    if req.email_from is not None:
        s.email_from = req.email_from
    if req.email_to is not None:
        s.email_to = req.email_to

    return {"status": "updated", "config": get_alerts_config()}


@router.post("/alerts/test")
def dispatch_test_alert() -> Dict[str, Any]:
    """Dispatch a test alert through all configured active channels."""
    mgr = serial_service.alert_manager
    dispatched = mgr.dispatch_test_alert(zone=mgr.settings.building_zone)
    return {
        "status": "dispatched" if dispatched else "failed_or_no_channels",
        "channels": mgr.settings.active_channels(),
    }
