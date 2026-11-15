"""
backend/app.py
FastAPI application for IoT Sensor Anomaly Detection System.
Provides REST APIs, WebSocket streaming, and static SPA serving.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import signal
import sys

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import ALLOWED_ORIGIN_REGEX, ALLOWED_ORIGINS
from backend.database import init_db
from backend.logging_config import StructuredLoggingMiddleware, setup_logging
from backend.routes.admin_routes import router as admin_router
from backend.routes.api_routes import router as api_router
from backend.routes.auth_routes import router as auth_router
from backend.routes.client_routes import router as client_router
from backend.routes.ws_routes import ws_manager, ws_router
from backend.services.serial_service import serial_service
from backend.shutdown import perform_graceful_shutdown


async def add_security_headers(request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ws: wss:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: configure logging, initialize database schema, and wire broadcast callback
    setup_logging()
    init_db()
    loop = asyncio.get_running_loop()
    serial_service.set_broadcast_callback(ws_manager.broadcast_json, loop)
    yield
    # Shutdown: perform complete graceful shutdown
    perform_graceful_shutdown()


def _signal_handler(signum, frame):
    perform_graceful_shutdown()
    sys.exit(0)


try:
    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)
except (ValueError, AttributeError):
    pass


app = FastAPI(
    title="IoT Sensor Anomaly Detection API",
    description="Full-stack API & WebSocket hub for ESP32+DHT11 unsupervised anomaly detection.",
    version="2.0.0",
    lifespan=lifespan,
)

# Register structured logging middleware
app.add_middleware(StructuredLoggingMiddleware)

# Add security headers middleware
app.middleware("http")(add_security_headers)

# Enable CORS strictly for allowed localhost origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    sanitized = []
    for err in exc.errors():
        clean_err = {
            "type": err.get("type"),
            "loc": err.get("loc"),
            "msg": err.get("msg"),
        }
        sanitized.append(clean_err)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": sanitized},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
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

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't intercept API or WebSocket calls; return 404 for unhandled API calls
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file() and full_path not in ("", "index.html"):
            return FileResponse(
                file_path,
                headers={
                    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;",
                    "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "strict-origin-when-cross-origin",
                },
            )
        return FileResponse(
            frontend_dist / "index.html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "strict-origin-when-cross-origin",
            },
        )


if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
