"""
backend/app.py
Main FastAPI application entry point.
Mounts client routes, admin routes, auth routes, WebSockets, and serves the static SPA frontend.
"""

from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.config import ALLOWED_ORIGINS, PROJECT_ROOT
from backend.database import init_db
from backend.routes.admin_routes import router as admin_router
from backend.routes.auth_routes import router as auth_router
from backend.routes.client_routes import router as client_router
from backend.routes.ws_routes import hub, router as ws_router
from backend.services.detector_service import detector_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Step 1: Initialize database tables on startup
    init_db()
    # Step 2: Set event loop on WebSocket hub
    hub.set_loop(asyncio.get_running_loop())
    # Step 3: Validate detector feature list at startup
    detector_service.load_models()
    yield
    # Step 4: Graceful shutdown
    pass


# Step 1: Initialize FastAPI app
app = FastAPI(
    title="IoT Climate Anomaly Detection System",
    description="Dual Client / Admin Digital Thermohygrograph and Anomaly Detection Suite",
    version="2.0.0",
    lifespan=lifespan,
)

# Step 2: Configure CORS middleware (localhost only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Step 3: Mount API and WebSocket routers
app.include_router(client_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(ws_router)

# Step 4: Serve built frontend SPA if available
frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Step 5: Don't intercept API or WebSocket calls
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return None
        candidate = frontend_dist / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend_dist / "index.html")
