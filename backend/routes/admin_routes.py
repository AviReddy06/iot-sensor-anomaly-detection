"""
backend/routes/admin_routes.py
Protected administrator REST API routes.
Requires signed token verification; provides model diagnostics, serial management,
evaluation metrics with data provenance, settings updates, and audit logging.
"""

from __future__ import annotations
import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
import pandas as pd
from backend.auth import require_admin_token
from backend.config import PROJECT_ROOT
from backend.database import get_audit_logs, get_setting, log_audit, set_setting
from backend.schemas.admin_schemas import BenchmarkMetricItem, ModelDetailsResponse
from backend.services.detector_service import detector_service
from backend.services.serial_service import serial_service

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin_token)])


@router.get("/model/details", response_model=ModelDetailsResponse)
def get_model_details():
    # Step 1: Return verified model parameters
    th = detector_service.thresholds
    return ModelDetailsResponse(
        version="v2.0-hybrid",
        commit_hash="10347c2",
        feature_cols=th.get("feature_cols", []),
        iforest_threshold=detector_service.active_threshold,
        sensitivity=detector_service.active_sensitivity,
        sensitivity_thresholds=detector_service.sensitivity_map,
        normal_temp_mean=th.get("normal_temp_mean", 25.67),
        normal_temp_std=th.get("normal_temp_std", 0.83),
        normal_hum_mean=th.get("normal_hum_mean", 61.42),
        normal_hum_std=th.get("normal_hum_std", 4.40),
    )


@router.get("/evaluation", response_model=List[BenchmarkMetricItem])
def get_evaluation_metrics():
    # Step 1: Load evaluation summary json
    summary_path = PROJECT_ROOT / "models" / "evaluation_summary.json"
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="evaluation_summary.json not found")

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Step 2: Format items with provenance and role
    results: List[BenchmarkMetricItem] = []
    meta = {
        "test": ("Recorded", "Development", "Legacy test set (35 shared rows with pilot)"),
        "pilot": ("Recorded", "Development", "Pilot dataset with post-hoc recovery tail annotations"),
        "eval_suite": ("Synthetic", "Held-out", "Injected mathematical faults (seed=42) on held-out clean normal trace"),
    }

    datasets_dict = data.get("datasets", {})
    for ds_name, (prov, role, note) in meta.items():
        if ds_name in datasets_dict:
            ds = datasets_dict[ds_name]
            for model_name, m in ds.items():
                results.append(
                    BenchmarkMetricItem(
                        dataset_name=ds_name,
                        detector=model_name,
                        row_count=m.get("rows", 0),
                        event_count=m.get("events_total", 0),
                        provenance=prov,
                        role=role,
                        tp=m.get("tp", 0),
                        fp=m.get("fp", 0),
                        fn=m.get("fn", 0),
                        tn=m.get("tn", 0),
                        precision=m.get("precision", 0.0),
                        recall=m.get("recall", 0.0),
                        f1=m.get("f1", 0.0),
                        pr_auc=m.get("pr_auc", 0.0),
                        roc_auc=m.get("roc_auc", 0.0),
                        note=note,
                    )
                )
    return results


@router.get("/serial/ports")
def get_serial_ports():
    # Step 1: Return port list excluding Bluetooth
    return serial_service.list_ports()


@router.get("/serial/status")
def get_serial_status():
    # Step 1: Return serial service status
    return serial_service.get_status()


@router.post("/serial/start")
def start_serial_port(payload: Dict[str, Any]):
    port = payload.get("port")
    baud = int(payload.get("baud", 115200))
    res = serial_service.start_hardware(port=port, baud=baud)
    log_audit("SERIAL_STARTED", "admin", f"Port: {port}, Baud: {baud}")
    return res


@router.post("/serial/stop")
def stop_serial_port():
    res = serial_service.stop_stream()
    log_audit("SERIAL_STOPPED", "admin", "Serial port connection closed")
    return res


@router.post("/simulation/start")
def start_simulation_stream(payload: Dict[str, Any]):
    dataset = str(payload.get("dataset", "test"))
    interval = float(payload.get("interval_sec", 1.0))
    res = serial_service.start_simulation(dataset_name=dataset, interval_sec=interval)
    log_audit("SIMULATION_STARTED", "admin", f"Dataset: {dataset}, Interval: {interval}s")
    return res


@router.post("/simulation/stop")
def stop_simulation_stream():
    res = serial_service.stop_stream()
    log_audit("SIMULATION_STOPPED", "admin", "Simulation replay stopped")
    return res


@router.get("/settings/sensitivity")
def get_sensitivity():
    return {
        "status": "ok",
        "sensitivity": detector_service.active_sensitivity,
        "threshold": detector_service.active_threshold,
        "sensitivity_map": detector_service.sensitivity_map,
    }


@router.post("/settings/sensitivity")
def update_sensitivity(payload: Dict[str, Any]):
    level = payload.get("level", "Medium")
    detector_service.set_sensitivity(level)
    set_setting("sensitivity", level)
    log_audit("SENSITIVITY_CHANGED", "admin", f"Sensitivity changed to {level}")
    return {"status": "updated", "sensitivity": level, "threshold": detector_service.active_threshold}


@router.get("/alerts/export")
def export_alerts_csv():
    # Step 1: Query events table from database
    from backend.database import get_recent_events
    events = get_recent_events(limit=1000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "start_time", "end_time", "duration_sec", "peak_temp", "peak_hum", "delta_temp", "what_changed", "severity", "sentence"])
    for e in events:
        writer.writerow([e["id"], e["start_time"], e["end_time"], e["duration_sec"], e["peak_temp"], e["peak_hum"], e["delta_temp"], e["what_changed"], e["severity"], e["sentence"]])
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=alert_history.csv"},
    )


@router.get("/audit")
def get_audit_trail(limit: int = Query(100, ge=1, le=500)):
    # Step 1: Retrieve audit log items
    return get_audit_logs(limit=limit)


@router.get("/datasets/overview")
def get_datasets_overview():
    return {
        "datasets": [
            {
                "name": "Training Baseline (Clean)",
                "rows": 34374,
                "time_range": "9 recorded sessions (< Nov 1, 2026)",
                "provenance": "Recorded (389 quarantined)",
                "role": "Training",
            },
            {
                "name": "Physical Pilot Data",
                "rows": 3084,
                "time_range": "2026-10-27 21:00:00 to 22:42:48",
                "provenance": "Recorded (relabelled post-hoc)",
                "role": "Development",
            },
            {
                "name": "Legacy Test Set",
                "rows": 55,
                "time_range": "2026-10-27 22:02:14 to 22:04:05",
                "provenance": "Recorded (single thermal event)",
                "role": "Development",
            },
            {
                "name": "Evaluation Suite",
                "rows": 1947,
                "time_range": "6 injected fault sequences",
                "provenance": "Synthetic injection (seed=42)",
                "role": "Held-out",
            },
        ],
        "overlap_note": "test.csv and pilot_data.csv share 35 identical rows between 22:02:14 and 22:03:23 on 2026-10-27. The pilot has no rows for 22:03:25 to 22:04:05 where the test event is located.",
    }


@router.get("/datasets/download/{filename}")
def download_dataset_csv(filename: str):
    # Step 1: Validate and resolve allowed dataset filename
    if filename == "clean_baseline.csv":
        file_path = PROJECT_ROOT / "data" / "processed" / "normal_data_clean.csv"
    elif filename == "test.csv":
        file_path = PROJECT_ROOT / "data" / "raw" / "test.csv"
    else:
        raise HTTPException(status_code=404, detail="Dataset file not found.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk.")

    # Step 2: Return file bytes directly as attachment
    return Response(
        content=file_path.read_bytes(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
