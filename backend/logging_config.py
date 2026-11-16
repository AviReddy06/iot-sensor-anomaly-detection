"""
backend/logging_config.py
Structured JSON logging middleware and access log redaction filter.
Ensures query parameter tokens (token=..., api_key=..., password=...) are never printed to console or logs.
"""

from __future__ import annotations
from datetime import datetime, timezone
import json
import logging
import re
import time
from typing import Any, Dict, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Regex to match sensitive query parameters and credential tokens
SENSITIVE_PARAM_REGEX = re.compile(
    r"((?:token|api_key|api-key|password|secret|auth)=)[^& \t\r\n\'\"]+",
    re.IGNORECASE,
)


def redact_sensitive_str(text: str) -> str:
    """Redacts values of sensitive query parameters from string."""
    if not text:
        return text
    return SENSITIVE_PARAM_REGEX.sub(r"\1[REDACTED]", text)


class AccessLogRedactionFilter(logging.Filter):
    """
    Filter applied to logging handlers (including uvicorn.access)
    to sanitize sensitive query parameters in formatted log strings.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args and isinstance(record.args, tuple):
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    new_args.append(redact_sensitive_str(arg))
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)

        if isinstance(record.msg, str):
            record.msg = redact_sensitive_str(record.msg)

        return True


class JSONStructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive_str(record.getMessage()),
        }
        if hasattr(record, "request_meta"):
            log_obj.update(getattr(record, "request_meta"))
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware recording structured JSON access records
    with guaranteed query token redaction.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        raw_query = request.url.query
        sanitized_query = redact_sensitive_str(raw_query)
        path = request.url.path

        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            meta = {
                "type": "access_log",
                "method": request.method,
                "path": path,
                "query": sanitized_query if sanitized_query else None,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else "unknown",
            }
            logger = logging.getLogger("backend.access")
            logger.info(
                f"{request.method} {path}{'?' + sanitized_query if sanitized_query else ''} {status_code} ({duration_ms}ms)",
                extra={"request_meta": meta},
            )


def setup_logging() -> None:
    """Configures redaction filters and structured formatting across logging subsystem."""
    redact_filter = AccessLogRedactionFilter()
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "backend.access", "httpx", "httpx2", "httpcore", "httpx._client", "httpx2._client", "httpcore._client"):
        log = logging.getLogger(name)
        log.addFilter(redact_filter)
        # Ensure propagation to root so root filter also applies
        log.propagate = True
        # Suppress INFO logs from httpx libraries to avoid token leakage
        if name.startswith("httpx") or name.startswith("httpcore"):
            log.setLevel(logging.WARNING)
    # Also add filter to root logger to catch any other loggers
    logging.getLogger().addFilter(redact_filter)
