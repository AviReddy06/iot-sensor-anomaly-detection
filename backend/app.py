"""
backend/app.py
FastAPI application for IoT Sensor Anomaly Detection System.
Provides REST APIs, WebSocket streaming, and static SPA serving.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import ALLOWED_ORIGINS
from backend.routes.admin_routes import router as admin_router
from backend.routes.api_routes import router as api_router
from backend.routes.auth_routes import router as auth_router
from backend.routes.client_routes import router as client_router
from backend.routes.ws_routes import ws_manager, ws_router
from backend.services.serial_service import serial_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: link serial service broadcast callback to active asyncio loop
    loop = asyncio.get_running_loop()
    serial_service.set_broadcast_callback(ws_manager.broadcast_json, loop)
    yield
    # Shutdown: stop any active serial or simulation workers
    serial_service.stop_stream()


app = FastAPI(
    title="IoT Sensor Anomaly Detection API",
    description="Full-stack API & WebSocket hub for ESP32+DHT11 unsupervised anomaly detection.",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable CORS strictly for allowed localhost origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API and WebSocket routes
app.include_router(client_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(api_router)
app.include_router(ws_router)

# Mount frontend production build if available
frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def serve_spa(full_path: str):
        # Don't intercept API or WebSocket calls; return 404 for unhandled API calls
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file() and full_path not in ("", "index.html"):
            return FileResponse(file_path)
        return FileResponse(
            frontend_dist / "index.html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )


if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
