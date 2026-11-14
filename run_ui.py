#!/usr/bin/env python3
"""
run_ui.py
Single launcher for the IoT Sensor Anomaly Detection Full-Stack Web Application.

Serves:
  - Frontend SPA: http://localhost:8000
  - REST API & Swagger Docs: http://localhost:8000/docs
  - Real-Time WebSocket: ws://localhost:8000/ws/telemetry
"""

from __future__ import annotations

import sys
from pathlib import Path
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("=" * 65)
    print("  AI-Based IoT Sensor Anomaly Detection - Full-Stack App")
    print("=" * 65)
    print("  • Web UI:        http://localhost:8000")
    print("  • API Swagger:   http://localhost:8000/docs")
    print("  • WebSocket:     ws://localhost:8000/ws/telemetry")
    print("  • Frontend Dev:  cd frontend && npm run dev (optional for HMR)")
    print("=" * 65)
    print("Starting Uvicorn server on http://0.0.0.0:8000 ... (Press Ctrl+C to stop)\n")

    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
