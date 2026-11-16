"""
backend/shutdown.py
Centralized graceful shutdown handler for SIGINT/SIGTERM and FastAPI lifespan teardown.
Ensures serial port release, event queue flushing, WebSocket cleanup,
and SQLite WAL checkpointing without unhandled traceback.
"""

from __future__ import annotations
import logging
import sys

logger = logging.getLogger("backend.shutdown")


def perform_graceful_shutdown() -> None:
    """Execute orderly cleanup across all active system subsystems."""
    logger.info("Initiating graceful shutdown sequence...")

    # 1. Stop serial streaming or simulation playback
    try:
        from backend.services.serial_service import serial_service
        serial_service.stop_stream()
    except Exception as exc:
        logger.warning(f"Error stopping serial service: {exc}")

    # 2. Flush and finalize active anomaly events
    try:
        from backend.services.events_service import events_service
        events_service.flush()
    except Exception as exc:
        logger.warning(f"Error flushing events service: {exc}")

    # 3. Shutdown WebSocket client sessions and cancel sender tasks
    try:
        from backend.routes.ws_routes import ws_manager
        ws_manager.shutdown()
    except Exception as exc:
        logger.warning(f"Error shutting down WebSocket manager: {exc}")

    # 4. Checkpoint WAL and cleanly close SQLite database connections
    try:
        from backend.database import close_db
        close_db()
    except Exception as exc:
        logger.warning(f"Error closing database: {exc}")

    logger.info("Graceful shutdown sequence completed.")
